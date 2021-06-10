from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from celery.result import AsyncResult

from .exceptions import InvalidDataException
from .validators import ChannelURLValidator


# Public API

AsyncTaskResult = AsyncResult


@dataclass(frozen=True)
class ChannelDataInput:
    #: The URL of the feed.
    url: str

    #: Type of channel
    channel_type: str
    #: The date the feed was last updated, according to the feed.
    # updated: Optional[datetime] = None

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
    fetch_succeeded: bool
    #: this maps to model.title_upstream
    title: Optional[str]
    link: Optional[str]


@dataclass(frozen=True)
class FetchedFeedEntry:
    feed_url: str
    gid: str
    link: Optional[str]
    title: Optional[str]
    author: Optional[str]
    published_time: Optional[datetime]
    #: this maps to model updated_time_upstream
    updated_time: Optional[datetime]
    content: tuple[str, ...]
    # FIXME: add enclosures support


@dataclass(frozen=True)
class FeedFetcherResult:
    #: List of fetched feed data;
    #: some are the same as what we already have, some are changed
    feeds: tuple[FetchedFeed, ...]

    #: List of fetched entries data;
    #: some are the same as what we already have, some are changed, some are new
    entries: tuple[FetchedFeedEntry, ...]
