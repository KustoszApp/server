from typing import Iterable

from celery import shared_task

from readorganizer_api.models import Channel


@shared_task
def fetch_channels_content(channel_ids: Iterable[int]):
    queryset = Channel.objects.get_queryset()
    channels = queryset.filter(pk__in=channel_ids)
    Channel.objects.fetch_channels_content(channels)
