from typing import Iterable

from celery import shared_task

from readorganizer_api.enums import InternalTasksEnum
from readorganizer_api.exceptions import SerialTaskAlreadyInProgress
from readorganizer_api.models import Channel
from readorganizer_api.utils import cache_lock


@shared_task(
    name=InternalTasksEnum.FETCH_FEED_CHANNEL_CONTENT,
    autoretry_for=(SerialTaskAlreadyInProgress,),
    retry_kwargs={"max_retries": 5},
    retry_backoff=True,
)
def fetch_feed_channel_content(channel_ids: Iterable[int], force_fetch: bool):
    with cache_lock as acquired_lock:
        if not acquired_lock:
            raise SerialTaskAlreadyInProgress()

        Channel.objects._fetch_feed_channels_content(channel_ids, force_fetch)
        # return ids of entries that were fetched?
        #        ids of next tasks we have scheduled?
        return channel_ids
