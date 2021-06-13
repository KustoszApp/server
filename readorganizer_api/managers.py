from collections import defaultdict
from dataclasses import asdict
from sys import maxsize as time_always_update
from typing import Iterable

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import models
from django.db import transaction
from django.db.models.query import QuerySet
from django.utils.timezone import now as django_now

from .enums import ChannelTypesEnum
from .enums import InternalTasksEnum
from .exceptions import NoNewChannelsAddedException
from .fetchers.feed import FeedChannelsFetcher
from .types import AddChannelResult
from .types import AddSingleChannelResult
from .types import AsyncTaskResult
from .types import ChannelDataInput
from .types import FetchedFeed
from .types import FetchedFeedEntry
from .utils import dispatch_task_by_name
from .utils import make_unique
from .utils import optional_make_aware


class ChannelManager(models.Manager):
    def add_channels(
        self, channels_list: Iterable[ChannelDataInput], fetch_content: bool = True
    ) -> AddChannelResult:
        queryset = self.get_queryset()
        channels_list = make_unique(channels_list)

        channel_results_map = {
            channel.url: {"url": channel.url, "added": False}
            for channel in channels_list
        }

        requested_urls = channel_results_map.keys()
        existing_urls = queryset.filter(url__in=requested_urls).values_list(
            "url", flat=True
        )
        new_urls = set(requested_urls) - set(existing_urls)

        if not new_urls:
            raise NoNewChannelsAddedException()

        channels_to_insert = []
        for channel_data in channels_list:
            if channel_data.url not in new_urls:
                continue

            map_obj = channel_results_map[channel_data.url]
            channel = self.model(**asdict(channel_data))
            try:
                channel.full_clean()
            except ValidationError as e:
                map_obj["exception"] = e
                continue
            map_obj["added"] = True
            channels_to_insert.append(channel)

        inserted_channels = queryset.bulk_create(channels_to_insert)

        if not inserted_channels[0].id:
            inserted_channels = queryset.filter(url__in=new_urls)

        fetch_content_tasks = []
        if fetch_content:
            fetch_content_tasks = self.fetch_channels_content(inserted_channels)

        channel_results = [
            AddSingleChannelResult(**channel_result)
            for channel_result in channel_results_map.values()
        ]

        rv = AddChannelResult(channel_results, fetch_content_tasks)
        return rv

    def fetch_channels_content(
        self, channels: QuerySet, force_fetch: bool = False
    ) -> tuple[AsyncTaskResult, ...]:
        active_channels = channels.filter(active=True).order_by("pk")

        feed_channels = active_channels.filter(channel_type=ChannelTypesEnum.FEED)

        feed_channels_paged = Paginator(
            feed_channels, settings.READORGANIZER_CHANNELS_CHUNK_SIZE
        )

        fetch_feeds_tasks = []
        for chunk_number in feed_channels_paged.page_range:
            task = self._request_feed_channels_content_fetch(
                feed_channels_paged.get_page(chunk_number), force_fetch
            )
            fetch_feeds_tasks.append(task)

        return fetch_feeds_tasks

    def _request_feed_channels_content_fetch(
        self, channels: QuerySet, force_fetch: bool
    ) -> AsyncTaskResult:
        channel_ids = [channel.id for channel in channels if channel.id]
        # FIXME: debugging only
        # self._fetch_feed_channels_content(channel_ids, force_fetch)
        # FIXME: debugging only
        task = dispatch_task_by_name(
            InternalTasksEnum.FETCH_FEED_CHANNEL_CONTENT,
            kwargs={"channel_ids": channel_ids, "force_fetch": force_fetch},
        )
        return task

    def __discard_channels_updated_recently(self, queryset: QuerySet):
        now = django_now()
        channels = []
        for channel in queryset:
            try:
                time_since_last_update = (now - channel.last_check_time).total_seconds()
            except TypeError:
                time_since_last_update = time_always_update

            if time_since_last_update > channel.update_frequency:
                channels.append(channel)
        return channels

    def __update_feeds_with_fetched_data(
        self, feeds_queryset: QuerySet, feeds_data: Iterable[FetchedFeed]
    ):
        updated_models = []
        right_now = django_now()
        feeds_data_map = {item.url: item for item in feeds_data}

        for channel_model in feeds_queryset:
            received_data = feeds_data_map.get(channel_model.url)
            if not received_data:
                continue
            channel_model.last_check_time = right_now
            if not received_data.fetch_failed:
                channel_model.last_successful_check_time = right_now
            if received_data.title != channel_model.title_upstream:
                channel_model.title_upstream = received_data.title
            if received_data.link != channel_model.link:
                channel_model.link = received_data.link
            updated_models.append(channel_model)

        feeds_queryset.bulk_update(
            updated_models,
            ("last_check_time", "last_successful_check_time", "title", "link"),
        )

    def __update_entries_with_fetched_data(
        self, feeds_queryset: QuerySet, entries_data: Iterable[FetchedFeedEntry]
    ):
        grouped_by_feed = defaultdict(list)
        for item in entries_data:
            grouped_by_feed[item.feed_url].append(item)

        for channel_model in feeds_queryset:
            channel_entries_data = grouped_by_feed.get(channel_model.url)
            channel_model.entries(
                manager="objects"
            )._create_or_update_with_fetched_data(
                channel_model=channel_model, entries_data=channel_entries_data
            )

    def _fetch_feed_channels_content(
        self, channel_ids: Iterable[int], force_fetch: bool
    ):  # return ids of entries that were fetched?
        queryset = self.get_queryset().filter(pk__in=channel_ids)

        if not force_fetch:
            requested_feeds = self.__discard_channels_updated_recently(queryset)
            requested_feed_urls = [feed.url for feed in requested_feeds]
        else:
            requested_feed_urls = queryset.values_list("url", flat=True)
            requested_feed_urls = list(requested_feed_urls)

        print(f"Will ask {len(requested_feed_urls)} feeds for updates")

        fetched_data = FeedChannelsFetcher.fetch(feed_urls=requested_feed_urls)
        print(f"Fetched data of {len(fetched_data.feeds)} feeds")
        print(f"Fetched data of {len(fetched_data.entries)} entries")

        self.__update_feeds_with_fetched_data(
            feeds_queryset=queryset, feeds_data=fetched_data.feeds
        )
        if fetched_data.entries:
            self.__update_entries_with_fetched_data(
                feeds_queryset=queryset, entries_data=fetched_data.entries
            )


class EntryManager(models.Manager):
    def _create_or_update_with_fetched_data(
        self, channel_model, entries_data: Iterable[FetchedFeedEntry]
    ):
        queryset = self.get_queryset()

        entries_data_map = {item.gid: item for item in entries_data}
        existing_qs = queryset.filter(
            channel=channel_model, gid__in=entries_data_map.keys()
        )

        existing_entries_map = {}
        for existing_entry in existing_qs:
            entry_data = entries_data_map.pop(existing_entry.gid)
            existing_entries_map[entry_data.gid] = entry_data

        if existing_entries_map:
            self.__update_existing_with_fetched_data(
                channel_model=channel_model,
                queryset=existing_qs,
                entries_data_map=existing_entries_map,
            )
        if entries_data_map:
            self.__create_new_from_fetched_data(
                channel_model=channel_model, entries_data_map=entries_data_map
            )

    def __update_existing_with_fetched_data(
        self, channel_model, queryset, entries_data_map
    ):
        print(f"considered for update: {len(entries_data_map)}")
        # FIXME: support content and enclosures
        updated_entries = []
        updated_fields = set()

        for entry_model in queryset:
            fetched_data = entries_data_map.get(entry_model.gid)
            (
                updated_model,
                model_updated_fields,
            ) = self.__update_single_model_with_fetched_data(entry_model, fetched_data)
            if model_updated_fields:
                updated_entries.append(updated_model)
                updated_fields.update(model_updated_fields)

        print(f"will update: {len(updated_entries)}")
        if not updated_entries:
            return

        updated_fields.add("updated_time")
        queryset.bulk_update(updated_entries, updated_fields)

    def __update_single_model_with_fetched_data(self, entry_model, fetched_data):
        keys_to_check = ("link", "title", "author", "published_time", "updated_time")
        model_updated_fields = set()

        for fetched_key in keys_to_check:
            fetched_value = getattr(fetched_data, fetched_key)
            if fetched_key in ("published_time", "updated_time"):
                fetched_value = optional_make_aware(fetched_value)
            model_key = fetched_key
            if fetched_key == "updated_time":
                model_key = "updated_time_upstream"
            model_value = getattr(entry_model, model_key)
            if model_value != fetched_value:
                print(
                    (
                        f"{entry_model.pk}: Will change {model_key} "
                        f"from {model_value} to {fetched_value}"
                    )
                )
                setattr(entry_model, model_key, fetched_value)
                model_updated_fields.add(model_key)

        if model_updated_fields:
            entry_model.updated_time = django_now()

        return entry_model, model_updated_fields

    def __create_new_from_fetched_data(self, channel_model, entries_data_map):
        print(f"will create: {len(entries_data_map)}")
        right_now = django_now()
        new_entries = []
        for entry_data in entries_data_map.values():
            entry = self.model(
                channel=channel_model,
                gid=entry_data.gid,
                link=entry_data.link,
                title=entry_data.title,
                author=entry_data.author,
                updated_time=right_now,
                published_time=optional_make_aware(entry_data.published_time),
                updated_time_upstream=optional_make_aware(entry_data.updated_time),
            )

            try:
                entry.full_clean()
            except ValidationError as e:
                print(e)
                continue
            EntryContent = entry.content_set.get_queryset().model
            entry_contents = []
            for fetched_content in entry_data.content:
                content_obj = EntryContent(
                    updated_time=right_now,
                    **{
                        key: getattr(fetched_content, key)
                        for key in ("source", "content", "language", "mimetype")
                    },
                )
                entry_contents.append(content_obj)
            new_entries.append({"entry": entry, "contents": entry_contents})

        with transaction.atomic():
            for entry_dict in new_entries:
                entry, contents = entry_dict.values()
                entry.save()
                print(f"{entry.pk}: will insert {len(contents)} content objects")
                if not entry_contents:
                    continue
                for content in contents:
                    content.entry = entry
                    content.save()
