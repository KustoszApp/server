from django_filters import rest_framework as drf_filters
from taggit.forms import TagField

from readorganizer_api import models


class NumberInFilter(drf_filters.BaseInFilter, drf_filters.NumberFilter):
    pass


class TagFilter(drf_filters.CharFilter):
    field_class = TagField

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("lookup_expr", "in")
        super().__init__(*args, **kwargs)


class EntryFilter(drf_filters.FilterSet):
    tags = TagFilter(field_name="tags__slug")
    tags__not = TagFilter(field_name="tags__slug", exclude=True)
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
    channel = drf_filters.NumberFilter(field_name="channel_id", lookup_expr="exact")
    channel__in = NumberInFilter(field_name="channel_id", lookup_expr="in")
    channel_tags = TagFilter(field_name="channel__tags__slug")
    channel_tags__not = TagFilter(field_name="channel__tags__slug", exclude=True)

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
