from celery import shared_task
from celery.utils.log import get_task_logger

from kustosz.enums import TaskNamesEnum
from kustosz.fetchers.feed import FeedChannelsFetcher


logger = get_task_logger(__name__)


@shared_task(
    name=TaskNamesEnum.CLEAN_FEED_FETCHER_CACHE,
)
def clean_feed_fetcher_cache() -> None:
    FeedChannelsFetcher.clean_cached_files()
