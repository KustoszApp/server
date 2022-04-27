from celery import shared_task
from celery.utils.log import get_task_logger

from kustosz.enums import TaskNamesEnum
from kustosz.fetchers.url import SingleURLFetcher


logger = get_task_logger(__name__)


@shared_task(
    name=TaskNamesEnum.CLEAN_URL_FETCHER_CACHE,
)
def clean_url_fetcher_cache() -> None:
    SingleURLFetcher.clean_cached_files()
