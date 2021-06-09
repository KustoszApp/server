from dataclasses import dataclass

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
