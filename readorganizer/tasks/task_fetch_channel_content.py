from typing import Iterable

from celery import shared_task

from readorganizer.enums import TaskNamesEnum
from readorganizer.models import Channel


@shared_task(
    name=TaskNamesEnum.FETCH_CHANNEL_CONTENT,
)
def fetch_channel_content(channel_ids: Iterable[int]):
    queryset = Channel.objects.get_queryset()
    channels = queryset.all()
    if channel_ids:
        channels = queryset.filter(pk__in=channel_ids)
    Channel.objects.fetch_channels_content(channels)
