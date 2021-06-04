from rest_framework import generics

from readorganizer_api import models
from readorganizer_api import serializers

# from rest_framework import permissions


class ChannelList(generics.ListAPIView):
    queryset = models.Channel.objects.all()
    serializer_class = serializers.ChannelSerializer
    # permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class ChannelDetail(generics.RetrieveAPIView):
    queryset = models.Channel.objects.all()
    serializer_class = serializers.ChannelDetailSerializer
    # permission_classes = [permissions.IsAuthenticatedOrReadOnly]
