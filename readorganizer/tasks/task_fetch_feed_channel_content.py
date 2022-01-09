from typing import Iterable

from celery import shared_task

from readorganizer.enums import TaskNamesEnum
from readorganizer.exceptions import SerialTaskAlreadyInProgress
from readorganizer.models import Channel
from readorganizer.utils import cache_lock


@shared_task(
    name=TaskNamesEnum.FETCH_FEED_CHANNEL_CONTENT,
    autoretry_for=(SerialTaskAlreadyInProgress,),
    retry_kwargs={"max_retries": 5},
    retry_backoff=5,
    retry_jitter=True,
)
def fetch_feed_channel_content(channel_ids: Iterable[int], force_fetch: bool):
    lock_id = TaskNamesEnum.FETCH_FEED_CHANNEL_CONTENT
    with cache_lock(lock_id, channel_ids) as acquired_lock:
        if not acquired_lock:
            raise SerialTaskAlreadyInProgress()

        Channel.objects._fetch_feed_channels_content(channel_ids, force_fetch)
        # return ids of entries that were fetched?
        #        ids of next tasks we have scheduled?
        return channel_ids
