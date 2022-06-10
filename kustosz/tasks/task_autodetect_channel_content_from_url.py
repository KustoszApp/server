from celery import shared_task
from celery.utils.log import get_task_logger

from kustosz.enums import TaskNamesEnum
from kustosz.exceptions import ChildrenTasksInProgress
from kustosz.utils.autodetect_content import AutodetectContent

logger = get_task_logger(__name__)


@shared_task(
    name=TaskNamesEnum.AUTODETECT_CHANNEL_CONTENT_FROM_URL,
    autoretry_for=(ChildrenTasksInProgress,),
    retry_kwargs={"max_retries": 360},
    retry_backoff=True,
    retry_backoff_max=10,
    retry_jitter=True,
)
def autodetect_channel_content_from_url(url):
    autodetect_content = AutodetectContent(url=url)
    channel_content = autodetect_content._run_channel_content()
    return channel_content
