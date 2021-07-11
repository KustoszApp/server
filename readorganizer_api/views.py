from django.db.models import Count
from django.db.models import Q
from django.db.models.functions import Coalesce
from rest_framework import generics

from readorganizer_api import filters
from readorganizer_api import models
from readorganizer_api import serializers

# from rest_framework import permissions


class ChannelList(generics.ListAPIView):
    queryset = models.Channel.objects.annotate(
        unarchived_entries=Count("entries", filter=Q(entries__archived=False))
    )
    serializer_class = serializers.ChannelSerializer
    # permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class ChannelDetail(generics.RetrieveAPIView):
    queryset = models.Channel.objects.annotate(
        unarchived_entries=Count("entries", filter=Q(entries__archived=False))
    )
    serializer_class = serializers.ChannelDetailSerializer
    # permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class EntriesList(generics.ListAPIView):
    queryset = models.Entry.objects.annotate(
        published_time=Coalesce("published_time_upstream", "updated_time_upstream")
    )
    serializer_class = serializers.EntrySerializer
    filterset_class = filters.EntryFilter
