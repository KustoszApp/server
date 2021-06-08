from dataclasses import dataclass

from celery.result import AsyncResult


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
