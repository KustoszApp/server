from celery import shared_task

from readorganizer_api.enums import InternalTasksEnum

# from readorganizer_api.models import Channel


@shared_task(name=InternalTasksEnum.FETCH_FEED_CHANNEL_CONTENT)
def fetch_feed_channel_content(channel_id: int):
    return channel_id
