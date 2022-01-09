from typing import Iterable

from celery import shared_task
from celery.utils.log import get_task_logger

from readorganizer.enums import TaskNamesEnum
from readorganizer.models import Channel
from readorganizer.types import AddChannelResult
from readorganizer.types import ChannelDataInput


logger = get_task_logger(__name__)


@shared_task(
    name=TaskNamesEnum.ADD_CHANNELS,
)
def add_channels(
    channels_list: Iterable[ChannelDataInput], fetch_content: bool = True
) -> AddChannelResult:
    return_value = Channel.objects.add_channels(channels_list, fetch_content)
    return return_value
