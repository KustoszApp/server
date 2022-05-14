import logging
from collections import defaultdict
from dataclasses import asdict
from datetime import timedelta
from sys import maxsize as time_always_update
from typing import Iterable
from typing import Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import models
from django.db import transaction
from django.db.models import Case
from django.db.models import Count
from django.db.models import Max
from django.db.models import Q
from django.db.models import TextField
from django.db.models import When
from django.db.models.functions import Coalesce
from django.db.models.query import QuerySet
from django.http import QueryDict
from django.utils.timezone import now as django_now

from .enums import ChannelTypesEnum
from .enums import TaskNamesEnum
from .exceptions import InvalidDataException
from .exceptions import NoNewChannelsAddedException
from .exceptions import PermanentFetcherError
from .fetchers.feed import FeedChannelsFetcher
from .fetchers.url import SingleURLFetcher
from .types import AddChannelResult
from .types import AddSingleChannelResult
from .types import AsyncTaskResult
from .types import ChannelDataInput
from .types import EntryDataInput
from .types import FetchedFeed
from .types import FetchedFeedEntry
from .types import ReadabilityContentList
from .utils import dispatch_task_by_name
from .utils import estimate_reading_time
from .utils import make_unique
from .utils import optional_make_aware
from .utils.duplicate_finder import DuplicateFinder
from .utils.extract_metadata import MetadataExtractor
from .utils.extract_readability import ReadabilityContentExtractor
from .utils.filter_actions import get_filter_action


log = logging.getLogger(__name__)


class ChannelManager(models.Manager):
    def get_annotated_queryset(self):
        return (
            super()
            .get_queryset()
            .exclude(channel_type=ChannelTypesEnum.MANUAL)
            .annotate(
                unarchived_entries=Count("entries", filter=Q(entries__archived=False)),
                tagged_entries=Count(
                    "entries", filter=Q(entries__tags__isnull=False), distinct=True
                ),
                total_entries=Count("entries"),
                last_entry_published_time=Max(
                    Coalesce(
                        "entries__published_time_upstream",
                        "entries__updated_time_upstream",
                    )
                ),
                displayed_title_sort=Case(
                    When(Q(title="") & Q(title_upstream=""), then="url"),
                    When(title="", then="title_upstream"),
                    default="title",
                    output_field=TextField(),
                ),
            )
        )

    def mark_as_inactive(self, queryset):
        archived_count = queryset.update(active=False)
        return archived_count

    def mark_as_active(self, queryset):
        archived_count = queryset.update(active=True)
        return archived_count

    def delete_channels(self, queryset, keep_tagged_entries=True):
        EntryManager = self.model.entries.rel.related_model.objects
        manual_channel = self.get_queryset().get(channel_type=ChannelTypesEnum.MANUAL)
        has_feeds = queryset.filter(channel_type=ChannelTypesEnum.FEED).exists()
        with transaction.atomic():
            if keep_tagged_entries:
                EntryManager.filter(
                    channel__in=queryset, tags__isnull=False
                ).distinct().update(channel=manual_channel, updated_time=django_now())
            deleted_count = queryset.delete()
        if has_feeds:
            dispatch_task_by_name(
                TaskNamesEnum.CLEAN_FEED_FETCHER_CACHE,
            )
        return deleted_count

    def add_channels(
        self, channels_list: Iterable[ChannelDataInput], fetch_content: bool = True
    ) -> AddChannelResult:
        log.debug("number of requested channels: %s", len(channels_list))
        queryset = self.get_queryset()
        channels_list = make_unique(channels_list)
        log.debug("number of unique channels: %s", len(channels_list))

        channel_results_map = {
            channel.url: {"url": channel.url, "added": False}
            for channel in channels_list
        }

        requested_urls = channel_results_map.keys()
        existing_urls = queryset.filter(url__in=requested_urls).values_list(
            "url", flat=True
        )
        new_urls = set(requested_urls) - set(existing_urls)
        log.debug("number of new channels: %s", len(new_urls))

        if not new_urls:
            raise NoNewChannelsAddedException()

        for channel_data in channels_list:
            if channel_data.url not in new_urls:
                continue

            map_obj = channel_results_map[channel_data.url]
            channel_data = asdict(channel_data)
            channel_tags = channel_data.pop("tags")
            channel = self.model(**channel_data)
            try:
                channel.full_clean()
            except ValidationError as e:
                map_obj["exception"] = e
                continue

            with transaction.atomic():
                channel.save()
                if channel_tags:
                    channel.tags.set(channel_tags)
                map_obj["added"] = True

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
        log.debug("number of channels in queryset: %s", channels.count())

        active_channels = (
            channels.exclude(channel_type=ChannelTypesEnum.MANUAL)
            .filter(active=True)
            .order_by("pk")
        )
        log.debug("number of active channels in queryset: %s", active_channels.count())

        feed_channels = active_channels.filter(channel_type=ChannelTypesEnum.FEED)

        if force_fetch and feed_channels:
            dispatch_task_by_name(
                TaskNamesEnum.CLEAN_FEED_FETCHER_CACHE,
            )

        feed_channels_paged = Paginator(
            feed_channels, settings.KUSTOSZ_FETCH_CHANNELS_CHUNK_SIZE
        )

        fetch_feeds_tasks = []
        for chunk_number in feed_channels_paged.page_range:
            task = self._request_feed_channels_content_fetch(
                feed_channels_paged.get_page(chunk_number), force_fetch
            )
            if task:
                fetch_feeds_tasks.append(task)

        return fetch_feeds_tasks

    def _request_feed_channels_content_fetch(
        self, channels: QuerySet, force_fetch: bool
    ) -> Optional[AsyncTaskResult]:
        if not channels:
            return None
        channel_ids = [channel.id for channel in channels if channel.id]
        task = dispatch_task_by_name(
            TaskNamesEnum.FETCH_FEED_CHANNEL_CONTENT,
            kwargs={"channel_ids": channel_ids, "force_fetch": force_fetch},
        )
        return task

    def _fetch_feed_channels_content(
        self, channel_ids: Iterable[int], force_fetch: bool
    ):  # return ids of entries that were fetched?
        queryset = self.get_queryset().filter(pk__in=channel_ids)

        if not force_fetch:
            requested_feeds = self.__discard_channels_updated_recently(queryset)
            requested_feed_urls = [feed.url for feed in requested_feeds]
            queryset = queryset.filter(url__in=requested_feed_urls)
        else:
            requested_feed_urls = queryset.values_list("url", flat=True)
            requested_feed_urls = list(requested_feed_urls)

        log.info("will update %s feeds", len(requested_feed_urls))
        log.debug("feeds urls: %s", requested_feed_urls)

        if not requested_feed_urls:
            return

        fetched_data = FeedChannelsFetcher.fetch(feed_urls=requested_feed_urls)
        log.debug("fetched data of %s feeds", len(fetched_data.feeds))
        log.debug("fetched data of %s entries in total", len(fetched_data.entries))
        fetch_failed_urls = [i.url for i in fetched_data.feeds if i.fetch_failed]
        if fetch_failed_urls:
            log.info("failed to fetch %s feeds", len(fetch_failed_urls))
            log.debug("failed to fetch feeds urls: %s", fetch_failed_urls)

        self.__update_feeds_with_fetched_data(
            feeds_queryset=queryset, feeds_data=fetched_data.feeds
        )
        if fetched_data.entries:
            self.__update_entries_with_fetched_data(
                feeds_queryset=queryset, entries_data=fetched_data.entries
            )
            dispatch_task_by_name(TaskNamesEnum.DEDUPLICATE_ENTRIES)
        log.info("feeds update complete")

    def __discard_channels_updated_recently(self, queryset: QuerySet):
        now = django_now()
        channels = []
        for channel in queryset:
            try:
                time_since_last_update = (now - channel.last_check_time).total_seconds()
            except TypeError:
                time_since_last_update = time_always_update

            log.debug(
                "channel %s seconds since last update: %s [channel url: %s]",
                channel.pk,
                time_since_last_update,
                channel.url,
            )

            if time_since_last_update > channel.update_frequency:
                channels.append(channel)
        return channels

    def __update_feeds_with_fetched_data(
        self, feeds_queryset: QuerySet, feeds_data: Iterable[FetchedFeed]
    ):
        updated_models = []
        feeds_data_map = {item.url: item for item in feeds_data}

        for channel_model in feeds_queryset:
            right_now = django_now()
            received_data = feeds_data_map.get(channel_model.url)
            if not received_data:
                log.warning(
                    (
                        "channel %s was requested for update, "
                        "but fetcher did not return it [channel url: %s]"
                    ),
                    channel_model.pk,
                    channel_model.url,
                )
                continue
            channel_model.last_check_time = right_now
            if not received_data.fetch_failed:
                channel_model.last_successful_check_time = right_now
                if received_data.title != channel_model.title_upstream:
                    log.debug(
                        (
                            "channel %s title_upstream changed "
                            "[channel url: %s ; old value '%s' ; new value '%s']"
                        ),
                        channel_model.pk,
                        channel_model.url,
                        channel_model.title_upstream,
                        received_data.title,
                    )
                    channel_model.title_upstream = received_data.title
                if received_data.link != channel_model.link:
                    log.debug(
                        (
                            "channel %s link changed "
                            "[channel url: %s ; old value '%s' ; new value '%s']"
                        ),
                        channel_model.pk,
                        channel_model.url,
                        channel_model.link,
                        received_data.link,
                    )
                    channel_model.link = received_data.link
            updated_models.append(channel_model)

        log.debug("number of feeds updated: %s", len(updated_models))
        feeds_queryset.bulk_update(
            updated_models,
            ("last_check_time", "last_successful_check_time", "title_upstream", "link"),
        )

    def __update_entries_with_fetched_data(
        self, feeds_queryset: QuerySet, entries_data: Iterable[FetchedFeedEntry]
    ):
        grouped_by_feed = defaultdict(list)
        for item in entries_data:
            grouped_by_feed[item.feed_url].append(item)

        entries_ids = set()
        for channel_model in feeds_queryset:
            channel_entries_data = grouped_by_feed.get(channel_model.url)
            if not channel_entries_data:
                log.info(
                    "channel %s did not fetch any new entries [channel url: %s]",
                    channel_model.pk,
                    channel_model.url,
                )
                continue
            new_or_updated_ids = channel_model.entries(
                manager="objects"
            )._create_or_update_with_fetched_data(
                channel_model=channel_model, entries_data=channel_entries_data
            )
            entries_ids.update(new_or_updated_ids)

        if entries_ids:
            dispatch_task_by_name(
                TaskNamesEnum.RUN_FILTERS_ON_ENTRIES,
                kwargs={"entries_ids": list(entries_ids)},
            )


class EntryManager(models.Manager):
    def get_annotated_queryset(self):
        return (
            super()
            .get_queryset()
            .annotate(
                published_time=Coalesce(
                    "published_time_upstream", "updated_time_upstream", "added_time"
                )
            )
        )

    def add_entry_from_manual_channel(self, entry_data: EntryDataInput):
        entry = self.model(
            channel_id=entry_data.channel,
            gid=entry_data.gid,
            link=entry_data.link,
            title=entry_data.title,
            author=entry_data.author,
            updated_time=django_now(),
            published_time_upstream=optional_make_aware(entry_data.published_time),
            updated_time_upstream=optional_make_aware(entry_data.updated_time),
        )
        try:
            entry.full_clean()
        except ValidationError as e:
            raise InvalidDataException(e)
        entry_exists = self.get_queryset().filter(
            channel=entry.channel_id, link__in=(entry.gid, entry.link)
        )
        if entry_exists.count():
            msg = "Entry with this Channel and Link already exists."
            raise InvalidDataException(msg)
        entry.save()
        dispatch_task_by_name(
            TaskNamesEnum.FETCH_MANUAL_ENTRY_DATA,
            kwargs={"entry_id": entry.pk},
        )
        return entry

    def deduplicate_entries(self, days=None) -> tuple[int, ...]:
        if not days:
            log.info(
                (
                    "deduplicate_entries called, but deduplication is disabled. "
                    "To enable it, set KUSTOSZ_DEDUPLICATE_DAYS to value "
                    "larger than 0."
                )
            )
            return
        duplicate_finder = DuplicateFinder()
        threshold_time = django_now() - timedelta(days=days)
        queryset = self.get_queryset()
        recent_entries = queryset.filter(added_time__gte=threshold_time)
        duplicate_ids = duplicate_finder.find_in(recent_entries)
        if not duplicate_ids:
            return duplicate_ids
        duplicates = recent_entries.filter(pk__in=duplicate_ids)
        log.info("Marking %s entries as duplicates", len(duplicate_ids))
        log.debug("entry ids: %s", ", ".join(map(str, duplicate_ids)))
        duplicates.update(archived=True, updated_time=django_now())
        return duplicate_ids

    def mark_as_archived(self, queryset):
        archived_count = queryset.update(archived=True, updated_time=django_now())
        return archived_count

    def _add_readability_contents(self, entry_id: int):
        entry = self.get_queryset().get(pk=entry_id)
        try:
            response = SingleURLFetcher.fetch(entry.link)
            extracted_content = ReadabilityContentExtractor.from_response(response)
        except PermanentFetcherError:
            extracted_content = ReadabilityContentList(content=())
        EntryContent = entry.content_set.get_queryset().model

        new_contents = []
        for fetched_content in extracted_content.content:
            reading_time = estimate_reading_time(fetched_content.content)
            content_obj = EntryContent(
                entry=entry,
                updated_time=django_now(),
                estimated_reading_time=reading_time,
                **asdict(fetched_content),
            )
            new_contents.append(content_obj)

        log.debug(
            "entry %s has %s new content objects [entry gid: %s]",
            entry.pk,
            len(new_contents),
            entry.gid,
        )

        with transaction.atomic():
            for content in new_contents:
                content.save()
            entry.readability_fetch_time = entry.updated_time = django_now()
            entry.save(update_fields=["readability_fetch_time", "updated_time"])

    def _create_or_update_with_fetched_data(
        self, channel_model, entries_data: Iterable[FetchedFeedEntry]
    ):
        log.info(
            "channel %s fetched entries: %s [channel url: %s]",
            channel_model.pk,
            len(entries_data),
            channel_model.url,
        )
        queryset = self.get_queryset()

        entries_data_map = {item.gid: item for item in entries_data}
        existing_qs = queryset.filter(
            channel=channel_model, gid__in=entries_data_map.keys()
        )
        log.debug("out of which already exist: %s", existing_qs.count())
        if len(entries_data) != len(entries_data_map):
            log.warning(
                (
                    "channel %s fetched entries with duplicated ids; "
                    "channel source might be misbehaving and data might be missing"
                    "[channel url: %s]"
                ),
                channel_model.pk,
                channel_model.url,
            )

        existing_entries_map = {}
        for existing_entry in existing_qs:
            entry_data = entries_data_map.pop(existing_entry.gid)
            existing_entries_map[entry_data.gid] = entry_data

        new_or_updated_ids = set()

        if existing_entries_map:
            self.__update_existing_with_fetched_data(
                channel_model=channel_model,
                queryset=existing_qs,
                entries_data_map=existing_entries_map,
            )
        if entries_data_map:
            new_entries_ids = self.__create_new_from_fetched_data(
                channel_model=channel_model, entries_data_map=entries_data_map
            )
            new_or_updated_ids.update(new_entries_ids)
            self._request_readability_contents(new_entries_ids)
        return new_or_updated_ids

    def _ensure_manual_entry_metadata(self, entry_id: int):
        entry = self.get_queryset().get(pk=entry_id)
        if entry.title and entry.author:
            log.debug(
                "Entry %s already has all metadata we can reasonably expect", entry.pk
            )
            return
        try:
            response = SingleURLFetcher.fetch(entry.link)
            new_metadata = MetadataExtractor.from_response(response)
        except PermanentFetcherError:
            new_metadata = MetadataExtractor.from_url(entry.link)

        # link is special, because it will always be present, but it could
        # redirect somewhere else (usually to track clicks). We want to store
        # final URL
        for key, value in asdict(new_metadata).items():
            old_value = getattr(entry, key)
            if not old_value or (key == "link" and value != old_value):
                log.debug(
                    "entry %s: setting %s to '%s' based on extracted metadata",
                    entry.pk,
                    key,
                    value,
                )
                setattr(entry, key, value)
        entry.updated_time = django_now()
        entry.save()

    def _request_readability_contents(self, entries_ids: Iterable[int]):
        if (
            not settings.KUSTOSZ_READABILITY_PYTHON_ENABLED
            and not settings.KUSTOSZ_READABILITY_NODE_ENABLED
        ):
            return

        for entry_id in entries_ids:
            dispatch_task_by_name(
                TaskNamesEnum.ADD_READABILITY_CONTENTS,
                kwargs={"entry_id": entry_id},
            )

    def _run_filters_on_entries(
        self, entries_ids: Iterable[int], entry_filters: QuerySet
    ):
        queryset = self.get_queryset().filter(pk__in=entries_ids)
        entry_filters = entry_filters.filter(enabled=True)
        if not entry_filters:
            return

        for filtering_rule in entry_filters:
            filtered_entries = self.__get_filtered_entries(filtering_rule, queryset)
            if not filtered_entries:
                continue
            log.info(
                "Filter %s matched for %s entries",
                filtering_rule.pk,
                len(filtered_entries),
            )
            log.debug(
                "Filter %s name: '%s'; action: '%s'; action_argument: '%s'",
                filtering_rule.pk,
                filtering_rule.name,
                filtering_rule.action_name,
                filtering_rule.action_argument,
            )
            log.debug(
                "matched entries ids: %s",
                ", ".join([str(e.pk) for e in filtered_entries]),
            )
            action = get_filter_action(filtering_rule.action_name)
            action(filtered_entries, filtering_rule.action_argument)

    def __get_filtered_entries(self, filtering_rule, queryset):
        from .filters import EntryFilter

        filtering_data = QueryDict(filtering_rule.condition)
        filter_ = EntryFilter(filtering_data, queryset)
        return filter_.qs

    def __update_existing_with_fetched_data(
        self, channel_model, queryset, entries_data_map
    ):
        log.debug(
            "channel %s number of entries considered for update: %s [channel url: %s]",
            channel_model.pk,
            len(entries_data_map),
            channel_model.url,
        )
        # FIXME: support enclosures
        updated_entries = []
        updated_fields = set()

        with transaction.atomic():
            for entry_model in queryset.prefetch_related("content_set"):
                fetched_data = entries_data_map.get(entry_model.gid)
                (
                    updated_model,
                    model_updated_fields,
                ) = self.__update_single_model_with_fetched_data(
                    entry_model, fetched_data
                )
                if model_updated_fields:
                    updated_entries.append(updated_model)
                    updated_fields.update(model_updated_fields)

            log.debug(
                "channel %s number of updated entries: %s [channel url: %s]",
                channel_model.pk,
                len(updated_entries),
                channel_model.url,
            )
            if not updated_entries:
                return

            queryset.bulk_update(updated_entries, updated_fields)

    def __create_new_from_fetched_data(self, channel_model, entries_data_map):
        log.debug("out of which are new: %s", len(entries_data_map))
        new_entries = []
        for entry_data in entries_data_map.values():
            entry = self.model(
                channel=channel_model,
                gid=entry_data.gid,
                link=entry_data.link,
                title=entry_data.title,
                author=entry_data.author,
                updated_time=django_now(),
                published_time_upstream=optional_make_aware(entry_data.published_time),
                updated_time_upstream=optional_make_aware(entry_data.updated_time),
            )

            try:
                entry.full_clean()
            except ValidationError as e:
                log.warning(
                    (
                        "channel %s: fetched entry with id '%s' is not valid:\n"
                        "%s\n[channel url: %s]"
                    ),
                    channel_model.pk,
                    entry.gid,
                    e,
                    channel_model.url,
                )
                continue
            EntryContent = entry.content_set.get_queryset().model
            entry_contents = []
            for fetched_content in entry_data.content:
                reading_time = estimate_reading_time(fetched_content.content)
                content_obj = EntryContent(
                    updated_time=django_now(),
                    estimated_reading_time=reading_time,
                    **{
                        key: getattr(fetched_content, key)
                        for key in ("source", "content", "language", "mimetype")
                    },
                )
                entry_contents.append(content_obj)
            new_entries.append({"entry": entry, "contents": entry_contents})

        entries_ids = []
        with transaction.atomic():
            for entry_dict in new_entries:
                entry, contents = entry_dict.values()
                entry.save()
                log.debug(
                    "entry %s has %s content objects [entry gid: %s]",
                    entry.pk,
                    len(contents),
                    entry.gid,
                )
                for content in contents:
                    content.entry = entry
                    content.save()
                entries_ids.append(entry.pk)
        return entries_ids

    def __update_single_model_with_fetched_data(self, entry_model, fetched_data):
        keys_to_check = ("link", "title", "author", "published_time", "updated_time")
        model_updated_fields = set()

        for fetched_key in keys_to_check:
            fetched_value = getattr(fetched_data, fetched_key)
            if fetched_key in ("published_time", "updated_time"):
                fetched_value = optional_make_aware(fetched_value)
            model_key = fetched_key
            if fetched_key in ("updated_time", "published_time"):
                model_key = f"{fetched_key}_upstream"
            model_value = getattr(entry_model, model_key)
            if model_value != fetched_value:
                log.debug(
                    "entry %s %s changed [old value: '%s'; new value: '%s']",
                    entry_model.pk,
                    model_key,
                    model_value,
                    fetched_value,
                )
                setattr(entry_model, model_key, fetched_value)
                model_updated_fields.add(model_key)

        content_set_changed = self.__update_single_model_content_set_with_fetched_data(
            entry_model, fetched_data
        )

        if model_updated_fields or content_set_changed:
            entry_model.updated_time = django_now()
            model_updated_fields.add("updated_time")

        return entry_model, model_updated_fields

    def __update_single_model_content_set_with_fetched_data(
        self, entry_model, fetched_data
    ):
        if not fetched_data.content:
            return False
        contents_data_map = {
            (content.source, content.mimetype, content.language): content
            for content in entry_model.content_set.all()
        }
        entry_contents_changed = False
        for fetched_entry_content in fetched_data.content:
            key = (
                fetched_entry_content.source,
                fetched_entry_content.mimetype,
                fetched_entry_content.language,
            )
            if key not in contents_data_map:
                reading_time = estimate_reading_time(fetched_entry_content.content)
                entry_model.content_set.create(
                    updated_time=django_now(),
                    estimated_reading_time=reading_time,
                    **{
                        key: getattr(fetched_entry_content, key)
                        for key in ("source", "content", "language", "mimetype")
                    },
                )
                entry_contents_changed = True
                continue
            existing_entry_content = contents_data_map.get(key)
            if existing_entry_content.content == fetched_entry_content.content:
                continue
            existing_entry_content.content = fetched_entry_content.content
            existing_entry_content.estimated_reading_time = estimate_reading_time(
                fetched_entry_content.content
            )
            existing_entry_content.updated_time = django_now()
            existing_entry_content.save()
            entry_contents_changed = True
        # FIXME: should we remove contents that disappeared from feed?
        return entry_contents_changed
