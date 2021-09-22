from rest_framework import generics
from rest_framework import status
from rest_framework.response import Response

from readorganizer_api import filters
from readorganizer_api import models
from readorganizer_api import serializers
from readorganizer_api.enums import InternalTasksEnum
from readorganizer_api.utils import dispatch_task_by_name

# from rest_framework import permissions


class ChannelsList(generics.ListAPIView):
    queryset = models.Channel.objects.get_annotated_queryset()
    serializer_class = serializers.ChannelsListSerializer
    filterset_class = filters.ChannelFilter
    # permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class ChannelDetail(generics.RetrieveUpdateAPIView):
    queryset = models.Channel.objects.get_annotated_queryset()
    serializer_class = serializers.ChannelSerializer
    # permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class EntriesList(generics.ListAPIView):
    queryset = models.Entry.objects.get_annotated_queryset()
    serializer_class = serializers.EntriesListSerializer
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


class EntryFiltersList(generics.ListCreateAPIView):
    queryset = models.EntryFilter.objects.all()
    serializer_class = serializers.EntryFilterSerializer


class EntryFilterDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = models.EntryFilter.objects.all()
    serializer_class = serializers.EntryFilterSerializer


class EntryFiltersRun(generics.CreateAPIView):
    queryset = models.EntryFilter.objects.all()
    filterset_class = filters.EntryFilter

    def create(self, request, *args, **kwargs):
        filtered_entries = self.filter_queryset(self.get_queryset())
        filtered_entries_ids = list(filtered_entries.values_list("pk", flat=True))
        entry_filter_ids = self.request.query_params.get("filter_ids", [])
        if entry_filter_ids:
            entry_filter_ids = map(int, entry_filter_ids.split(","))
        dispatch_task_by_name(
            InternalTasksEnum.RUN_FILTERS_ON_ENTRIES,
            kwargs={
                "entries_ids": filtered_entries_ids,
                "entry_filter_ids": entry_filter_ids,
            },
        )
        headers = self.get_success_headers([])
        return Response([], status=status.HTTP_200_OK, headers=headers)


class ChannelsInactivate(generics.CreateAPIView):
    queryset = models.Channel.objects.get_annotated_queryset().filter(active=True)
    serializer_class = serializers.ChannelsInactivateSerializer
    filterset_class = filters.ChannelFilter

    def create(self, request, *args, **kwargs):
        filtered_channels = self.filter_queryset(self.get_queryset())
        inactivated_channels = list(filtered_channels.values_list("pk", flat=True))
        inactivated_count = models.Channel.objects.mark_as_inactive(filtered_channels)
        serializer = self.get_serializer(
            data={
                "inactivated_count": inactivated_count,
                "inactivated_channels": inactivated_channels,
            }
        )
        serializer.is_valid(raise_exception=True)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)


class ChannelsActivate(generics.CreateAPIView):
    queryset = models.Channel.objects.get_annotated_queryset().filter(active=False)
    serializer_class = serializers.ChannelsActivateSerializer
    filterset_class = filters.ChannelFilter

    def create(self, request, *args, **kwargs):
        filtered_channels = self.filter_queryset(self.get_queryset())
        activated_channels = list(filtered_channels.values_list("pk", flat=True))
        activated_count = models.Channel.objects.mark_as_active(filtered_channels)
        serializer = self.get_serializer(
            data={
                "activated_count": activated_count,
                "activated_channels": activated_channels,
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
