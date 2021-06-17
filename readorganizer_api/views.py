from django.db.models import Count
from django.db.models import Q
from rest_framework import generics

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
