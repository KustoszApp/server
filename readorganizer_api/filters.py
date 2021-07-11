from django_filters import rest_framework as drf_filters

from readorganizer_api import models


class EntryFilter(drf_filters.FilterSet):
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
