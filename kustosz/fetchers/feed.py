import enum
import tempfile
from pathlib import Path
from typing import Iterable
from typing import Optional

from django.conf import settings
from reader import Entry
from reader import EntryUpdateStatus
from reader import FeedExistsError
from reader import make_reader
from reader.plugins import DEFAULT_PLUGINS as READER_DEFAULT_PLUGINS

from kustosz.constants import FEED_FETCHER_LOCAL_FEEDS_DIR
from kustosz.constants import FETCHERS_CACHE_DIR
from kustosz.enums import EntryContentSourceTypesEnum
from kustosz.types import FeedFetcherResult
from kustosz.types import FetchedFeed
from kustosz.types import FetchedFeedEntry
from kustosz.types import FetchedFeedEntryContent


def normalize_paths_for_reader(paths):
    new_paths = []
    for path in paths:
        if path.startswith("file://"):
            path = local_url_to_reader_feed_url(path)
        new_paths.append(path)
    return new_paths


def normalize_path_for_kustosz(path):
    if path.startswith("file:"):
        return reader_feed_url_to_local_url(path)
    return path


def local_url_to_reader_feed_url(path):
    without_prefix = path.removeprefix("file://")
    return f"file:{without_prefix}"


def reader_feed_url_to_local_url(path):
    without_prefix = path.removeprefix("file:")
    return f"file://{without_prefix}"


def aggressive_ua_fallback_plugin(reader):
    # this is almost verbatim copy of reader.plugins.ua_fallback, except
    # that it uses User-Agent set in Kustosz settings. If this User-Agent
    # represents real browser, it may help with some particularly stubborn
    # websites
    def aggressive_ua_fallback_hook(session, response, request, **kwargs):
        if not response.status_code == 403:
            return None

        ua = settings.KUSTOSZ_URL_FETCHER_EXTRA_HEADERS.get("User-Agent")
        if not ua:
            return None

        request.headers["User-Agent"] = ua

        return request

    reader._parser.session_hooks.response.append(aggressive_ua_fallback_hook)


class FeedFetcherPurpose(enum.Enum):
    MAIN = enum.auto()
    FEED_DISCOVERY = enum.auto()


class FeedChannelsFetcher:
    def __init__(self, purpose: FeedFetcherPurpose):
        self._purpose = purpose
        self._prepare_directories()
        self._db_file = self._get_db_file()
        self._fetched_entries = []

        feed_root = FEED_FETCHER_LOCAL_FEEDS_DIR
        if self._purpose == FeedFetcherPurpose.FEED_DISCOVERY:
            feed_root = FETCHERS_CACHE_DIR

        self._reader = make_reader(
            url=str(self._db_file),
            feed_root=str(feed_root),
            plugins=READER_DEFAULT_PLUGINS + [aggressive_ua_fallback_plugin],
        )
        self._reader.after_entry_update_hooks.append(self._reader_plugin())

    def _reader_plugin(self):
        fetched_entries = self._fetched_entries

        def inner(reader, entry: Entry, status: EntryUpdateStatus):
            fetched_entries.append((entry.feed_url, entry.id))

        return inner

    def _prepare_directories(self):
        for d in (FETCHERS_CACHE_DIR, FEED_FETCHER_LOCAL_FEEDS_DIR):
            d.mkdir(mode=0o700, exist_ok=True)

    def _get_db_file(self):
        if self._purpose == FeedFetcherPurpose.FEED_DISCOVERY:
            if not settings.DEBUG:
                return ":memory:"
            _, db_path = tempfile.mkstemp(".sqlite", dir=FETCHERS_CACHE_DIR)
            return Path(db_path)

        db_name = f"readerdb.{self._purpose.name}.sqlite"
        return FETCHERS_CACHE_DIR / db_name

    def _remove_db_from_cache(self):
        db_name = self._db_file.name
        for path in self._db_file.parent.glob("*"):
            if path.is_file() and db_name in path.name:
                path.unlink(missing_ok=True)

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

    def _get_new_feeds_data(self):
        fetched_feeds: tuple[FetchedFeed, ...] = []
        for feed in self._reader.get_feeds(updates_enabled=True):
            obj_data = {
                "url": normalize_path_for_kustosz(feed.url),
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
                if value:
                    if key == "feed_url":
                        value = normalize_path_for_kustosz(value)
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

    def update(self, feed_urls: Iterable[str]):
        self._disable_updates_for_existing_feeds()
        self._add_feeds(normalize_paths_for_reader(feed_urls))
        self._reader.update_feeds(workers=settings.KUSTOSZ_FEED_READER_WORKERS)

    def get_new_data(self):
        feeds_data = self._get_new_feeds_data()
        entries_data = self._get_new_entries_data()
        rv = FeedFetcherResult(feeds=feeds_data, entries=entries_data)
        return rv

    @classmethod
    def fetch(
        cls,
        feed_urls: Iterable[str],
        purpose: Optional[FeedFetcherPurpose] = FeedFetcherPurpose.MAIN,
    ) -> FeedFetcherResult:
        fetcher = cls(purpose=purpose)
        fetcher.update(feed_urls)
        rv = fetcher.get_new_data()
        return rv

    @classmethod
    def clean_cached_files(cls):
        fetcher = cls(purpose=FeedFetcherPurpose.MAIN)
        fetcher._remove_db_from_cache()
