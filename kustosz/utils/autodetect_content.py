import dataclasses
import tempfile
import urllib.parse
from collections import defaultdict
from io import BytesIO
from itertools import chain
from operator import attrgetter
from pathlib import Path
from typing import Mapping
from typing import Sequence
from typing import Union

from dacite import Config as DaciteConfig
from dacite import from_dict as dataclass_from_dict
from django.core.cache import cache
from lxml import etree

from kustosz.celery import app as celery_app
from kustosz.constants import AUTODETECT_CHANNEL_ENTRIES_MAX
from kustosz.constants import AUTODETECT_RESULTS_EXPIRE_TIME
from kustosz.constants import FETCHERS_CACHE_DIR
from kustosz.enums import AsyncTaskStatesEnum
from kustosz.enums import TaskNamesEnum
from kustosz.exceptions import ChildrenTasksInProgress
from kustosz.fetchers.feed import FeedChannelsFetcher
from kustosz.fetchers.feed import FeedFetcherPurpose
from kustosz.fetchers.url import SingleURLFetcher
from kustosz.types import AutodetectContentTaskResult
from kustosz.types import AutodetectedChannel
from kustosz.types import AutodetectedEntry
from kustosz.types import FeedFetcherResult
from kustosz.utils import dispatch_task_by_name
from kustosz.utils import make_unique
from kustosz.utils import normalize_url
from kustosz.utils.extract_metadata import MetadataExtractor


class TaskInProgress:
    pass


class EmptyResult:
    pass


def as_feed_url(elem, parsed_url) -> str:
    if elem_type := elem.get("type"):
        if "xml" not in elem_type.lower():
            return

    feed_indicators = ("feed", "rss", "atom")
    attr_content = (
        elem_type or "",
        elem.get("title") or "",
        elem.get("href") or "",
        " ".join(elem.itertext()),
    )

    for value in attr_content:
        value = value.lower()
        if any(indicator in value for indicator in feed_indicators):
            break
    else:
        return

    href = elem.get("href")

    if href.startswith("//"):
        return f"{parsed_url.scheme}:{href}"

    if href.startswith("/") or not href.lower().startswith("http"):
        full_url = parsed_url._replace(path=href)
        return urllib.parse.urlunparse(full_url)

    return href


def content_is_feed(content) -> bool:
    parser = etree.XMLParser(ns_clean=True, recover=True, encoding="utf-8")
    response_content = BytesIO(content.encode("utf-8"))
    try:
        parsed_content = etree.parse(response_content, parser)
    except etree.LxmlError:
        return False

    root_elem = parsed_content.getroot()
    if root_elem is None:
        return False
    root_tag_name = etree.QName(root_elem).localname
    return root_tag_name.lower() in ("feed", "rss")


def entries_grouped_by_feed(
    fetched_data: FeedFetcherResult,
) -> Mapping[str, Sequence["AutodetectedEntry"]]:
    grouped_by_feed = defaultdict(list)

    for entry in fetched_data.entries:
        discovered_entry = AutodetectedEntry(
            gid=entry.gid,
            link=entry.link,
            title=entry.title,
            author=entry.author,
            published_time_upstream=entry.published_time,
            updated_time_upstream=entry.updated_time,
        )
        grouped_by_feed[entry.feed_url].append(discovered_entry)

    for key in grouped_by_feed.keys():
        grouped_by_feed.get(key).sort(key=attrgetter("published_time"), reverse=True)

    return grouped_by_feed


class FeedLinksFinder:
    def __init__(self, url, response):
        self._url = url
        self._response = response
        self._filenames_to_check = (
            "feed",
            "feed.xml",
            "index.xml",
            "rss.xml",
            "atom.xml",
        )

    def _from_url(self, url):
        parsed_url = urllib.parse.urlparse(url)
        current_path = Path("/")
        if parsed_url.path:
            current_path = Path(parsed_url.path)

        while True:
            for filename in self._filenames_to_check:
                path = current_path / filename
                parsed_with_path = parsed_url._replace(path=str(path))
                yield urllib.parse.urlunparse(parsed_with_path)

            if current_path == current_path.parent:
                break
            current_path = current_path.parent

    def _from_response(self):
        parsed_url = urllib.parse.urlparse(self._response.url)
        parser = etree.HTMLParser(encoding="utf-8")
        response_content = BytesIO(self._response.text.encode("utf-8"))
        parsed_content = etree.parse(response_content, parser)
        selectors = (
            '//link[@href][@rel="alternate"]',
            '//link[@href][@name="alternate"]',
            '//link[@href][@rel="alternative"]',
            "//a[@href]",
        )
        for selector in selectors:
            matching_elems = parsed_content.xpath(selector)
            for elem in matching_elems:
                full_url = as_feed_url(elem, parsed_url)
                if not full_url:
                    continue
                yield normalize_url(full_url)

    def _find_links(self):
        sources = [
            self._from_url(self._url),
        ]

        if self._response.url != self._url:
            sources.append(self._from_url(self._response.url))

        if not content_is_feed(self._response.text):
            sources.append(self._from_response())

        for link in chain(*sources):
            yield link

    @classmethod
    def find_links(cls, url, response):
        finder = cls(url, response)
        links = finder._find_links()
        return make_unique(links)


class AutodetectContent:
    def __init__(self, url, **kwargs):
        self._url = url
        self._dacite_config = DaciteConfig()

    def _celery_task_start_or_result(
        self, task_name, cache_key
    ) -> celery_app.AsyncResult:
        cached_task_id = cache.get(cache_key)
        if cached_task_id:
            return celery_app.AsyncResult(cached_task_id)

        celery_task = dispatch_task_by_name(
            task_name,
            kwargs={"url": self._url},
        )
        cache.set(
            cache_key, celery_task.task_id, timeout=AUTODETECT_RESULTS_EXPIRE_TIME
        )
        return celery_task

    def _run_from_url(self) -> AutodetectContentTaskResult:
        cache_key = f"autodetect:{self._url}"
        celery_task = self._celery_task_start_or_result(
            TaskNamesEnum.AUTODETECT_CONTENT_FROM_URL, cache_key
        )

        if not celery_task.ready():
            return AutodetectContentTaskResult(state=AsyncTaskStatesEnum.IN_PROGRESS)

        if celery_task.state == "FAILURE":
            return AutodetectContentTaskResult(state=AsyncTaskStatesEnum.FAILED)

        dto_entries = []
        for entry in celery_task.result.get("entries"):
            dto_entry = dataclass_from_dict(
                data_class=AutodetectedEntry,
                data=entry,
                config=self._dacite_config,
            )
            dto_entries.append(dto_entry)

        dto_channels = []
        for channel in celery_task.result.get("channels"):
            dto_channel = dataclass_from_dict(
                data_class=AutodetectedChannel,
                data=channel,
                config=self._dacite_config,
            )
            dto_channels.append(dto_channel)

        return AutodetectContentTaskResult(
            state=AsyncTaskStatesEnum.COMPLETED,
            entries=dto_entries,
            channels=dto_channels,
        )

    def _run_content_task(self):
        # hotload cache for children tasks
        SingleURLFetcher.fetch(self._url)

        discovered_entry = self._entry_content()
        discovered_channel = self._channel_content()
        discovered_channels = self._channels()
        all_results = (discovered_entry, discovered_channel, discovered_channels)

        if any(result is TaskInProgress for result in all_results):
            raise ChildrenTasksInProgress()

        entries = []
        if discovered_entry is not EmptyResult:
            entry = dataclasses.asdict(discovered_entry)
            entries.append(entry)

        all_discovered_channels = []
        if discovered_channel is not EmptyResult:
            all_discovered_channels.append(discovered_channel)
        if discovered_channels is not EmptyResult:
            all_discovered_channels.extend(discovered_channels)

        channels = []
        for discovered_channel_item in all_discovered_channels:
            channel = dataclasses.asdict(discovered_channel_item)
            channels.append(channel)

        # FIXME: remove? essentially, that would happen if we thought we have
        # feed, but then reader is unable to parse it, and we failed to autodetect
        # any other feed from content or url
        if not entries and not channels:
            entry = AutodetectedEntry(gid=self._url, link=self._url)
            entry = dataclasses.asdict(entry)
            entries.append(entry)

        return {
            "state": AsyncTaskStatesEnum.COMPLETED,
            "entries": entries,
            "channels": channels,
        }

    def _entry_content(self) -> Union[AutodetectedEntry, EmptyResult, TaskInProgress]:
        cache_key = f"autodetect_entry_content:{self._url}"
        celery_task = self._celery_task_start_or_result(
            TaskNamesEnum.AUTODETECT_ENTRY_CONTENT_FROM_URL, cache_key
        )

        if not celery_task.ready():
            return TaskInProgress

        if celery_task.state == "FAILURE":
            return EmptyResult

        task_result = celery_task.result
        if not task_result:
            return EmptyResult

        return dataclass_from_dict(
            data_class=AutodetectedEntry,
            data=task_result,
            config=self._dacite_config,
        )

    def _run_entry_content(self) -> dict:
        response = SingleURLFetcher.fetch(self._url)

        # probably a binary data, like PDF or image - allow to add as a bookmark
        response_type = response.headers.get("Content-Type")
        if not response_type or not ("xml" in response_type or "html" in response_type):
            entry = AutodetectedEntry(gid=self._url, link=self._url)
            return dataclasses.asdict(entry)

        # probably a feed - let _channel_content handle it
        if content_is_feed(response.text):
            return {}

        new_metadata = MetadataExtractor.from_response(response)
        discovered_entry = AutodetectedEntry(
            gid=self._url,
            **dataclasses.asdict(new_metadata),
        )
        return dataclasses.asdict(discovered_entry)

    def _channel_content(
        self,
    ) -> Union[AutodetectedChannel, EmptyResult, TaskInProgress]:
        cache_key = f"autodetect_channel_content:{self._url}"
        celery_task = self._celery_task_start_or_result(
            TaskNamesEnum.AUTODETECT_CHANNEL_CONTENT_FROM_URL, cache_key
        )

        if not celery_task.ready():
            return TaskInProgress

        if celery_task.state == "FAILURE":
            return EmptyResult

        task_result = celery_task.result
        if not task_result:
            return EmptyResult

        return dataclass_from_dict(
            data_class=AutodetectedChannel,
            data=task_result,
            config=self._dacite_config,
        )

    def _run_channel_content(self):
        response = SingleURLFetcher.fetch(self._url)

        with tempfile.NamedTemporaryFile(dir=FETCHERS_CACHE_DIR) as fp:
            fp.write(response.text.encode("utf-8"))
            fp.flush()
            file_name = Path(fp.name).name
            fetched_data = FeedChannelsFetcher.fetch(
                feed_urls=[f"file://{file_name}"],
                purpose=FeedFetcherPurpose.FEED_DISCOVERY,
            )

        channel_data = fetched_data.feeds[0]

        # probably not a feed
        if channel_data.fetch_failed:
            return {}

        grouped_by_feed = entries_grouped_by_feed(fetched_data)
        channel_entries = grouped_by_feed.get(channel_data.url)

        discovered_channel = AutodetectedChannel(
            url=self._url,
            title_upstream=channel_data.title,
            link=channel_data.link,
            entries=channel_entries[:AUTODETECT_CHANNEL_ENTRIES_MAX],
            total_entries=len(channel_entries),
        )

        return dataclasses.asdict(discovered_channel)

    def _channels(
        self,
    ) -> Union[Sequence["AutodetectedChannel"], EmptyResult, TaskInProgress]:
        cache_key = f"autodetect_channels:{self._url}"
        celery_task = self._celery_task_start_or_result(
            TaskNamesEnum.AUTODETECT_CHANNELS_FROM_URL, cache_key
        )

        if not celery_task.ready():
            return TaskInProgress

        if celery_task.state == "FAILURE":
            return EmptyResult

        task_result = celery_task.result
        if not task_result:
            return EmptyResult

        channels_list = []
        for channel_data in task_result:
            discovered_channel = dataclass_from_dict(
                data_class=AutodetectedChannel,
                data=channel_data,
                config=self._dacite_config,
            )
            channels_list.append(discovered_channel)

        return channels_list

    def _run_channels(self):
        response = SingleURLFetcher.fetch(self._url)

        feed_urls = FeedLinksFinder.find_links(url=self._url, response=response)

        fetched_data = FeedChannelsFetcher.fetch(
            feed_urls=feed_urls,
            purpose=FeedFetcherPurpose.FEED_DISCOVERY,
        )

        if all(channel_data.fetch_failed for channel_data in fetched_data.feeds):
            return []

        grouped_by_feed = entries_grouped_by_feed(fetched_data)

        discovered_channels = []
        for channel_data in fetched_data.feeds:
            if channel_data.fetch_failed:
                continue
            channel_entries = grouped_by_feed[channel_data.url]
            discovered_channel = AutodetectedChannel(
                url=channel_data.url,
                title_upstream=channel_data.title,
                link=channel_data.link,
                entries=channel_entries[:AUTODETECT_CHANNEL_ENTRIES_MAX],
                total_entries=len(channel_entries),
            )
            discovered_channels.append(dataclasses.asdict(discovered_channel))
        return discovered_channels

    @classmethod
    def from_url(cls, url: str, **kwargs) -> AutodetectContentTaskResult:
        autodetect = cls(url=url, **kwargs)
        task_data = autodetect._run_from_url()
        return task_data
