from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from typing import Sequence

from celery.result import AsyncResult

from .constants import DEFAULT_UPDATE_FREQUENCY
from .exceptions import InvalidDataException
from .utils import normalize_url
from .validators import ChannelURLValidator
from .validators import EntryURLValidator


# Public API

AsyncTaskResult = AsyncResult


@dataclass(frozen=True)
class ChannelDataInput:
    #: The URL of the feed.
    url: str

    #: Type of channel
    channel_type: str

    #: Title of channel
    title: Optional[str] = ""

    #: Is this channel active?
    active: Optional[bool] = True

    #: How often should channel be checked for new content, in seconds
    update_frequency: Optional[int] = DEFAULT_UPDATE_FREQUENCY

    #: Tags of channel
    tags: Sequence[str] = ()

    def __post_init__(self):
        channel_url_validator = ChannelURLValidator()
        try:
            channel_url_validator(self.url)
        except Exception as e:
            msg = f"Following URL is not valid: {self.url}"
            raise InvalidDataException(msg) from e

    def __hash__(self):
        return hash(self.url)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.url == other.url


@dataclass(frozen=True)
class EntryDataInput:
    #: Internal id of channel this entry originates from
    channel: int

    #: URL of entry
    link: str

    #: Unique identifier of entry
    gid: Optional[str] = ""

    #: Title (subject) of entry
    title: Optional[str] = ""

    #: Author of entry
    author: Optional[str] = ""

    #: Publication date of entry
    published_time: Optional[datetime] = None

    #: When entry/channel claims entry was last updated
    updated_time: Optional[datetime] = None

    #: Tags of channel
    tags: Sequence[str] = ()

    def __post_init__(self):
        entry_url_validator = EntryURLValidator()
        try:
            entry_url_validator(self.link)
        except Exception as e:
            msg = f"Following URL is not valid: {self.link}"
            raise InvalidDataException(msg) from e
        if not self.gid:
            object.__setattr__(self, "gid", normalize_url(self.link))

    def __hash__(self):
        return hash(self.gid)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.gid == other.gid


@dataclass(frozen=True)
class AddSingleChannelResult:
    #: The URL of the feed
    url: str

    #: Was this channel added?
    added: bool

    #: Exception raised while trying to add channel
    exception: Optional[InvalidDataException] = None


@dataclass(frozen=True)
class AddChannelResult:
    #: Details of requested channels
    channels: tuple[AddSingleChannelResult, ...]

    #: Tasks created when adding channels
    tasks: tuple[AsyncTaskResult, ...]


@dataclass(frozen=True)
class FetchedFeed:
    url: str
    fetch_failed: bool
    #: this maps to model.title_upstream
    title: Optional[str] = ""
    link: Optional[str] = ""


@dataclass(frozen=True)
class FetchedFeedEntryContent:
    source: str
    content: str
    mimetype: Optional[str] = ""
    language: Optional[str] = ""


@dataclass(frozen=True)
class FetchedFeedEntry:
    feed_url: str
    gid: str
    link: Optional[str] = ""
    title: Optional[str] = ""
    author: Optional[str] = ""
    published_time: Optional[datetime] = None
    #: this maps to model updated_time_upstream
    updated_time: Optional[datetime] = None
    content: Sequence["FetchedFeedEntryContent"] = ()
    # FIXME: add enclosures support


@dataclass(frozen=True)
class FeedFetcherResult:
    #: List of fetched feed data;
    #: some are the same as what we already have, some are changed
    feeds: tuple[FetchedFeed, ...]

    #: List of fetched entries data;
    #: some are the same as what we already have, some are changed, some are new
    entries: tuple[FetchedFeedEntry, ...]


@dataclass(frozen=True)
class ReadabilityContentList:
    content: Sequence["FetchedFeedEntryContent"] = ()


@dataclass(frozen=True)
class SingleEntryExtractedMetadata:
    #: Author of entry
    author: Optional[str] = ""

    #: URL of entry
    link: Optional[str] = ""

    #: Title (subject) of entry
    title: Optional[str] = ""

    #: Publication date of entry
    published_time_upstream: Optional[datetime] = None

    #: When entry/channel claims entry was last updated
    updated_time_upstream: Optional[datetime] = None


@dataclass(frozen=True)
class AutodetectedEntry:
    # this maps to serializers.AutodetectedEntrySerializer
    gid: str
    link: str
    title: Optional[str] = ""
    author: Optional[str] = ""
    published_time_upstream: Optional[datetime] = None
    updated_time_upstream: Optional[datetime] = None
    published_time: Optional[datetime] = None

    def __post_init__(self):
        if not self.published_time:
            published_time = None
            if self.published_time_upstream:
                published_time = self.published_time_upstream
            elif self.updated_time_upstream:
                published_time = self.updated_time_upstream
            if published_time:
                object.__setattr__(self, "published_time", published_time)


@dataclass(frozen=True)
class AutodetectedChannel:
    # this maps to serializers.AutodetectedChannelSerializer
    url: str
    title_upstream: Optional[str] = ""
    link: Optional[str] = ""
    total_entries: Optional[int] = 0
    last_entry_published_time: Optional[datetime] = None
    entries: Sequence["AutodetectedEntry"] = ()

    def __post_init__(self):
        if not self.total_entries:
            object.__setattr__(self, "total_entries", len(self.entries))

        if not self.last_entry_published_time:
            last_entry_published_time = None
            for entry in self.entries:
                if not entry.published_time:
                    continue
                if (
                    not last_entry_published_time
                    or entry.published_time > last_entry_published_time
                ):
                    last_entry_published_time = entry.published_time
            if last_entry_published_time:
                object.__setattr__(
                    self, "last_entry_published_time", last_entry_published_time
                )


@dataclass(frozen=True)
class AutodetectContentTaskResult:
    state: str
    entries: Sequence["AutodetectedEntry"] = ()
    channels: Sequence["AutodetectedChannel"] = ()
