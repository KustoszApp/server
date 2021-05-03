from rest_framework import generics

from readorganizer_api import models
from readorganizer_api import serializers

# from rest_framework import permissions


class FeedList(generics.ListAPIView):
    queryset = models.Feed.objects.all()
    serializer_class = serializers.FeedSerializer
    # permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class FeedDetail(generics.RetrieveAPIView):
    queryset = models.Feed.objects.all()
    serializer_class = serializers.FeedDetailSerializer
    # permission_classes = [permissions.IsAuthenticatedOrReadOnly]
