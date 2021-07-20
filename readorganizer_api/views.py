from rest_framework import generics
from rest_framework import status
from rest_framework.response import Response

from readorganizer_api import filters
from readorganizer_api import models
from readorganizer_api import serializers

# from rest_framework import permissions


class ChannelsList(generics.ListAPIView):
    queryset = models.Channel.objects.get_annotated_queryset()
    serializer_class = serializers.ChannelSerializer
    # permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class ChannelDetail(generics.RetrieveUpdateAPIView):
    queryset = models.Channel.objects.get_annotated_queryset()
    serializer_class = serializers.ChannelDetailSerializer
    # permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class EntriesList(generics.ListAPIView):
    queryset = models.Entry.objects.get_annotated_queryset()
    serializer_class = serializers.ListEntrySerializer
    filterset_class = filters.EntryFilter


class EntryDetail(generics.RetrieveUpdateAPIView):
    queryset = models.Entry.objects.get_annotated_queryset()
    serializer_class = serializers.EntrySerializer


class EntriesArchive(generics.CreateAPIView):
    queryset = models.Entry.objects.get_annotated_queryset()
    serializer_class = serializers.EntriesArchiveSerializer
    filterset_class = filters.EntryFilter

    def create(self, request, *args, **kwargs):
        filtered_entries = self.filter_queryset(self.get_queryset())
        archived_entries = list(filtered_entries.values_list("pk", flat=True))
        archived_count = models.Entry.objects.mark_as_archived(filtered_entries)
        serializer = self.get_serializer(
            data={
                "archived_count": archived_count,
                "archived_entries": archived_entries,
            }
        )
        serializer.is_valid(raise_exception=True)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)


class ChannelTagsList(generics.ListAPIView):
    queryset = models.Channel.tags.all()
    serializer_class = serializers.TagsListSerializer


class EntryTagsList(generics.ListAPIView):
    queryset = models.Entry.tags.all()
    serializer_class = serializers.TagsListSerializer
