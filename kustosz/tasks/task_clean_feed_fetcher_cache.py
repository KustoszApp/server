from celery import shared_task
from celery.utils.log import get_task_logger

from kustosz.enums import SerialQueuesNamesEnum
from kustosz.enums import TaskNamesEnum
from kustosz.exceptions import SerialTaskAlreadyInProgress
from kustosz.fetchers.feed import FeedChannelsFetcher
from kustosz.utils import cache_lock


logger = get_task_logger(__name__)


@shared_task(
    name=TaskNamesEnum.CLEAN_FEED_FETCHER_CACHE,
    autoretry_for=(SerialTaskAlreadyInProgress,),
    retry_kwargs={"max_retries": 5},
    retry_backoff=5,
    retry_jitter=True,
)
def clean_feed_fetcher_cache() -> None:
    lock_id = SerialQueuesNamesEnum.FEED_FETCHER
    with cache_lock(lock_id, TaskNamesEnum.CLEAN_FEED_FETCHER_CACHE) as acquired_lock:
        if not acquired_lock:
            raise SerialTaskAlreadyInProgress()

        FeedChannelsFetcher.clean_cached_files()
