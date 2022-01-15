from typing import Iterable

from django.conf import settings
from reader import Entry
from reader import EntryUpdateStatus
from reader import FeedExistsError
from reader import make_reader

from readorganizer.constants import FEED_FETCHER_LOCAL_FEEDS_DIR
from readorganizer.constants import FETCHERS_CACHE_DIR
from readorganizer.enums import EntryContentSourceTypesEnum
from readorganizer.types import FeedFetcherResult
from readorganizer.types import FetchedFeed
from readorganizer.types import FetchedFeedEntry
from readorganizer.types import FetchedFeedEntryContent


class FeedChannelsFetcher:
    def __init__(self, feed_urls: Iterable[str]):
        self._prepare_directories()
        self._db_file = FETCHERS_CACHE_DIR / "readerdb.sqlite"
        self._fetched_entries = []
        self._reader = make_reader(
            url=str(self._db_file), feed_root=str(FEED_FETCHER_LOCAL_FEEDS_DIR)
        )
        self._reader.after_entry_update_hooks.append(self._reader_plugin())
        self._feed_urls = self._normalize_paths_for_reader(feed_urls)

    def _reader_plugin(self):
        fetched_entries = self._fetched_entries

        def inner(reader, entry: Entry, status: EntryUpdateStatus):
            fetched_entries.append((entry.feed_url, entry.id))

        return inner

    def _prepare_directories(self):
        for d in (FETCHERS_CACHE_DIR, FEED_FETCHER_LOCAL_FEEDS_DIR):
            d.mkdir(mode=0o700, exist_ok=True)

    @classmethod
    def _normalize_paths_for_reader(cls, paths):
        new_paths = []
        for path in paths:
            if cls._is_local_url(path):
                path = cls._local_url_to_reader_feed_url(path)
            new_paths.append(path)
        return new_paths

    @staticmethod
    def _is_local_url(path):
        return path.startswith("file://")

    @staticmethod
    def _local_url_to_reader_feed_url(path):
        without_prefix = path.removeprefix("file://")
        return f"file:{without_prefix}"

    @classmethod
    def _normalize_output_path(cls, path):
        if path.startswith("file:"):
            return cls._reader_feed_url_to_local_url(path)
        return path

    @staticmethod
    def _reader_feed_url_to_local_url(path):
        without_prefix = path.removeprefix("file:")
        return f"file://{without_prefix}"

    def _disable_updates_for_existing_feeds(self):
        feeds = self._reader.get_feeds(updates_enabled=True)
        for feed in feeds:
            self._reader.disable_feed_updates(feed)

    def _add_feeds(self, feed_urls: Iterable[str]):
        for feed in feed_urls:
            try:
                self._reader.add_feed(feed)
            except FeedExistsError:
                self._reader.enable_feed_updates(feed)
                self._mark_all_entries_as_read(feed)

    def _mark_all_entries_as_read(self, feed: str):
        entries = self._reader.get_entries(feed=feed, read=False)
        for entry in entries:
            self._reader.mark_entry_as_read(entry)

    def _get_new_feeds_data(self):
        fetched_feeds: tuple[FetchedFeed, ...] = []
        for feed in self._reader.get_feeds(updates_enabled=True):
            obj_data = {
                "url": self._normalize_output_path(feed.url),
                "fetch_failed": bool(feed.last_exception),
            }
            if feed.title:
                obj_data["title"] = feed.title
            if feed.link:
                obj_data["link"] = feed.link

            obj = FetchedFeed(**obj_data)
            fetched_feeds.append(obj)
        return fetched_feeds

    def _get_new_entries_data(self):
        fetched_entries: tuple[FetchedFeedEntry, ...] = []
        data_mapping = (
            # DTO key, reader key
            ("feed_url", "feed_url"),
            ("gid", "id"),
            ("link", "link"),
            ("title", "title"),
            ("author", "author"),
            ("published_time", "published"),
            ("updated_time", "updated"),
        )
        for entry_definition in self._fetched_entries:
            entry = self._reader.get_entry(entry_definition)
            obj_data = {}
            for key, reader_key in data_mapping:
                value = getattr(entry, reader_key, None)
                if key == "feed_url":
                    value = self._normalize_output_path(value)
                if value:
                    obj_data[key] = value

            contents = []
            if entry.summary:
                content_obj = FetchedFeedEntryContent(
                    source=EntryContentSourceTypesEnum.FEED_SUMMARY,
                    content=entry.summary,
                )
                contents.append(content_obj)
            for entry_content in entry.content:
                content_data = {
                    "source": EntryContentSourceTypesEnum.FEED_CONTENT,
                    "content": entry_content.value,
                }
                if entry_content.type:
                    content_data["mimetype"] = entry_content.type
                if entry_content.language:
                    content_data["language"] = entry_content.language

                content_obj = FetchedFeedEntryContent(**content_data)
                contents.append(content_obj)
            if contents:
                obj_data["content"] = tuple(contents)

            obj = FetchedFeedEntry(**obj_data)
            fetched_entries.append(obj)
        return fetched_entries

    def update(self):
        self._disable_updates_for_existing_feeds()
        self._add_feeds(self._feed_urls)
        self._reader.update_feeds(workers=settings.READORGANIZER_FEED_READER_WORKERS)

    def get_new_data(self):
        feeds_data = self._get_new_feeds_data()
        entries_data = self._get_new_entries_data()
        rv = FeedFetcherResult(feeds=feeds_data, entries=entries_data)
        return rv

    @classmethod
    def fetch(cls, feed_urls: Iterable[str]) -> FeedFetcherResult:
        fetcher = cls(feed_urls)
        fetcher.update()
        rv = fetcher.get_new_data()
        return rv
