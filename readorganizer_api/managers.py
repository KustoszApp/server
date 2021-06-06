from dataclasses import asdict
from typing import Iterable

from django.db import models
from django.db.models.query import QuerySet

from .enums import ChannelTypesEnum
from .enums import InternalTasksEnum
from .exceptions import NoNewChannelsAddedException
from .types import AsyncTaskResult
from .types import ChannelDataInput
from .utils import dispatch_task_by_name


class ChannelManager(models.Manager):
    def add_channels(
        self, channels_list: Iterable[ChannelDataInput], fetch_content: bool = True
    ) -> tuple[tuple[int, ...], tuple[AsyncTaskResult, ...]]:
        queryset = self.get_queryset()

        all_urls = [channel.uri for channel in channels_list]
        existing_urls = queryset.filter(uri__in=all_urls).values_list("uri", flat=True)
        new_urls = set(all_urls) - set(existing_urls)

        if not new_urls:
            raise NoNewChannelsAddedException()

        channels_to_insert = [
            self.model(**asdict(channel_data))
            for channel_data in channels_list
            if channel_data.uri in new_urls
        ]

        inserted_channels = queryset.bulk_create(channels_to_insert)

        if not inserted_channels[0].id:
            inserted_channels = queryset.filter(uri__in=new_urls)

        fetch_content_tasks = []
        if fetch_content:
            fetch_content_tasks = self.fetch_channels_content(inserted_channels)

        inserted_channels_ids = [channel.id for channel in inserted_channels]

        return (inserted_channels_ids, fetch_content_tasks)

    def fetch_channels_content(self, channels: QuerySet) -> tuple[AsyncTaskResult, ...]:
        active_channels = channels.filter(active=True)

        feed_channels = active_channels.filter(channel_type=ChannelTypesEnum.FEED)

        fetch_feed_tasks = self._request_feed_channels_content_fetch(feed_channels)

        return fetch_feed_tasks

    def _request_feed_channels_content_fetch(
        self, channels: QuerySet
    ) -> tuple[AsyncTaskResult, ...]:
        fetch_feed_tasks = []
        for channel in channels:
            if not channel.id:
                print("dostałem kanał, który nie ma id")
                # something went wrong - log
                continue
            task = dispatch_task_by_name(
                InternalTasksEnum.FETCH_FEED_CHANNEL_CONTENT,
                kwargs={"channel_id": channel.id},
            )
            fetch_feed_tasks.append(task)
        return fetch_feed_tasks
