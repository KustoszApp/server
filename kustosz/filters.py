from django.core.validators import EMPTY_VALUES
from django_filters import rest_framework as drf_filters
from taggit.forms import TagField

from kustosz import models


class EmptyStringFilter(drf_filters.BooleanFilter):
    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        exclude = self.exclude ^ (value is False)
        method = qs.exclude if exclude else qs.filter

        return method(**{self.field_name: ""})


class NumberInFilter(drf_filters.BaseInFilter, drf_filters.NumberFilter):
    pass


class TagFilter(drf_filters.CharFilter):
    field_class = TagField

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("lookup_expr", "in")
        kwargs.setdefault("distinct", True)
        super().__init__(*args, **kwargs)


class ReadingTimeFilter(drf_filters.NumberFilter):
    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        # as a naive optimization, get ids of entries that have at least
        # one content matching criteria
        # this has better chance of helping when lookup_expr is gt or gte
        lookup = f"estimated_reading_time__{self.lookup_expr}"
        entries_ids = [entry.pk for entry in qs]
        contents = models.EntryContent.objects.filter(
            entry__in=entries_ids,
            **{lookup: value},
        )
        naively_filtered_entries = set(contents.values_list("entry", flat=True))

        filtered_entries_ids = set()
        for entry in qs:
            if entry.pk not in naively_filtered_entries:
                continue
            estimated_reading_time = entry.preferred_content.estimated_reading_time
            if self.lookup_expr == "exact" and estimated_reading_time == value:
                filtered_entries_ids.add(entry.pk)
            elif self.lookup_expr == "gt" and estimated_reading_time > value:
                filtered_entries_ids.add(entry.pk)
            elif self.lookup_expr == "gte" and estimated_reading_time >= value:
                filtered_entries_ids.add(entry.pk)
            elif self.lookup_expr == "lt" and estimated_reading_time < value:
                filtered_entries_ids.add(entry.pk)
            elif self.lookup_expr == "lte" and estimated_reading_time <= value:
                filtered_entries_ids.add(entry.pk)

        return qs.filter(pk__in=filtered_entries_ids)


class ChannelFilter(drf_filters.FilterSet):
    tags = TagFilter(field_name="tags__slug")
    tags__not = TagFilter(field_name="tags__slug", exclude=True)
    has_tags = drf_filters.BooleanFilter(
        field_name="tags", lookup_expr="isnull", exclude=True
    )
    id = NumberInFilter(field_name="pk", lookup_expr="in")
    id__not = NumberInFilter(field_name="pk", lookup_expr="in", exclude=True)
    last_entry_published_time = drf_filters.IsoDateTimeFilter(
        field_name="last_entry_published_time", lookup_expr="exact"
    )
    last_entry_published_time__lt = drf_filters.IsoDateTimeFilter(
        field_name="last_entry_published_time", lookup_expr="lt"
    )
    last_entry_published_time__gt = drf_filters.IsoDateTimeFilter(
        field_name="last_entry_published_time", lookup_expr="gt"
    )
    last_entry_published_time__lte = drf_filters.IsoDateTimeFilter(
        field_name="last_entry_published_time", lookup_expr="lte"
    )
    last_entry_published_time__gte = drf_filters.IsoDateTimeFilter(
        field_name="last_entry_published_time", lookup_expr="gte"
    )
    is_stale = drf_filters.BooleanFilter(
        field_name="is_stale", method="get_stale_channels"
    )

    order = drf_filters.OrderingFilter(
        fields=(
            "id",
            "url",
            "title",
            "link",
            "last_check_time",
            "last_successful_check_time",
            "added_time",
        )
    )

    class Meta:
        model = models.Channel
        fields = {
            "url": [
                "exact",
                "iexact",
                "contains",
                "icontains",
                "startswith",
                "istartswith",
                "endswith",
                "iendswith",
            ],
            "title": [
                "exact",
                "iexact",
                "contains",
                "icontains",
                "startswith",
                "istartswith",
                "endswith",
                "iendswith",
            ],
            "title_upstream": [
                "exact",
                "iexact",
                "contains",
                "icontains",
                "startswith",
                "istartswith",
                "endswith",
                "iendswith",
            ],
            "link": [
                "exact",
                "iexact",
                "contains",
                "icontains",
                "startswith",
                "istartswith",
                "endswith",
                "iendswith",
            ],
            "last_check_time": ["exact", "lt", "gt", "lte", "gte"],
            "last_successful_check_time": ["exact", "lt", "gt", "lte", "gte"],
            "added_time": ["exact", "lt", "gt", "lte", "gte"],
            "active": ["exact"],
            "update_frequency": ["exact", "lt", "gt", "lte", "gte"],
        }

    def get_stale_channels(self, queryset, field_name, value):
        selected_channels = []
        for channel in queryset:
            if channel.is_stale is value:
                selected_channels.append(channel.pk)
        return queryset.filter(pk__in=selected_channels)


class EntryFilter(drf_filters.FilterSet):
    tags = TagFilter(field_name="tags__slug")
    tags__not = TagFilter(field_name="tags__slug", exclude=True)
    has_tags = drf_filters.BooleanFilter(
        field_name="tags", lookup_expr="isnull", exclude=True
    )
    published_time = drf_filters.IsoDateTimeFilter(
        field_name="published_time", lookup_expr="exact"
    )
    published_time__lt = drf_filters.IsoDateTimeFilter(
        field_name="published_time", lookup_expr="lt"
    )
    published_time__gt = drf_filters.IsoDateTimeFilter(
        field_name="published_time", lookup_expr="gt"
    )
    published_time__lte = drf_filters.IsoDateTimeFilter(
        field_name="published_time", lookup_expr="lte"
    )
    published_time__gte = drf_filters.IsoDateTimeFilter(
        field_name="published_time", lookup_expr="gte"
    )
    channel = NumberInFilter(field_name="channel_id", lookup_expr="in")
    channel__not = NumberInFilter(
        field_name="channel_id", lookup_expr="in", exclude=True
    )
    channel_tags = TagFilter(field_name="channel__tags__slug")
    channel_tags__not = TagFilter(field_name="channel__tags__slug", exclude=True)
    channel_has_tags = drf_filters.BooleanFilter(
        field_name="channel__tags", lookup_expr="isnull", exclude=True
    )
    has_note = EmptyStringFilter(field_name="note", exclude=True)
    # as implementation detail, django-filter will apply filters in order
    # of class variables definition. By putting this last, we hope
    # to avoid going through all entries in db
    reading_time = ReadingTimeFilter(
        field_name="preferred_content__estimated_reading_time", lookup_expr="exact"
    )
    reading_time__lt = ReadingTimeFilter(
        field_name="preferred_content__estimated_reading_time", lookup_expr="lt"
    )
    reading_time__gt = ReadingTimeFilter(
        field_name="preferred_content__estimated_reading_time", lookup_expr="gt"
    )
    reading_time__lte = ReadingTimeFilter(
        field_name="preferred_content__estimated_reading_time", lookup_expr="lte"
    )
    reading_time__gte = ReadingTimeFilter(
        field_name="preferred_content__estimated_reading_time", lookup_expr="gte"
    )
    order = drf_filters.OrderingFilter(
        fields=(
            "id",
            "link",
            "added_time",
            "updated_time",
            "published_time_upstream",
            "updated_time_upstream",
            "published_time",
        )
    )

    class Meta:
        model = models.Entry
        fields = {
            "archived": ["exact"],
            "link": [
                "exact",
                "iexact",
                "contains",
                "icontains",
                "startswith",
                "istartswith",
                "endswith",
                "iendswith",
            ],
            "title": [
                "exact",
                "iexact",
                "contains",
                "icontains",
                "startswith",
                "istartswith",
                "endswith",
                "iendswith",
            ],
            "added_time": ["exact", "lt", "gt", "lte", "gte"],
            "updated_time": ["exact", "lt", "gt", "lte", "gte"],
            "published_time_upstream": ["exact", "lt", "gt", "lte", "gte"],
            "updated_time_upstream": ["exact", "lt", "gt", "lte", "gte"],
        }
