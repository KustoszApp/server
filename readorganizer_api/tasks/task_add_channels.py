from typing import Iterable

from celery import shared_task
from celery.utils.log import get_task_logger

from readorganizer_api.models import Channel
from readorganizer_api.types import AsyncTaskResult
from readorganizer_api.types import ChannelDataInput


logger = get_task_logger(__name__)


@shared_task()
def add_channels(
    channels_list: Iterable[ChannelDataInput], fetch_content: bool = True
) -> tuple[tuple[int, ...], tuple[AsyncTaskResult, ...]]:
    return_value = Channel.objects.add_channels(channels_list, fetch_content)
    return return_value
