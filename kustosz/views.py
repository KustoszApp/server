from datetime import timedelta

from django.utils.timezone import now as django_now
from rest_framework import generics
from rest_framework import permissions
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from kustosz import filters
from kustosz import models
from kustosz import serializers
from kustosz.enums import ChannelTypesEnum
from kustosz.enums import TaskNamesEnum
from kustosz.exceptions import InvalidDataException
from kustosz.types import ChannelDataInput
from kustosz.utils import dispatch_task_by_name


class UserDetail(generics.RetrieveUpdateAPIView):
    serializer_class = serializers.UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChannelsList(generics.ListCreateAPIView):
    queryset = models.Channel.objects.get_annotated_queryset().order_by(
        "displayed_title_sort", "id"
    )
    serializer_class = serializers.ChannelSerializer
    filterset_class = filters.ChannelFilter
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        channel = ChannelDataInput(
            url=serializer.data.get("url"),
            channel_type=ChannelTypesEnum.FEED,
            title=serializer.data.get("title", ""),
            tags=serializer.data.get("tags"),
        )
        models.Channel.objects.add_channels([channel], fetch_content=True)


class ChannelDetail(generics.RetrieveUpdateAPIView):
    queryset = models.Channel.objects.get_annotated_queryset()
    serializer_class = serializers.ChannelSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_update(self, serializer):
        if "url" not in serializer.validated_data:
            super().perform_update(serializer)
            return

        serializer.save(last_check_time=django_now() - timedelta(days=365))
        dispatch_task_by_name(
            TaskNamesEnum.FETCH_FEED_CHANNEL_CONTENT,
            kwargs={"channel_ids": [serializer.data.get("id")], "force_fetch": False},
        )


class EntriesList(generics.ListAPIView):
    queryset = models.Entry.objects.get_annotated_queryset().order_by(
        "-published_time", "id"
    )
    serializer_class = serializers.EntriesListSerializer
    filterset_class = filters.EntryFilter
    permission_classes = [permissions.IsAuthenticated]


class EntryDetail(generics.RetrieveUpdateAPIView):
    queryset = models.Entry.objects.get_annotated_queryset()
    serializer_class = serializers.EntrySerializer
    permission_classes = [permissions.IsAuthenticated]


class EntriesArchive(generics.CreateAPIView):
    queryset = models.Entry.objects.get_annotated_queryset()
    serializer_class = serializers.EntriesArchiveSerializer
    filterset_class = filters.EntryFilter
    permission_classes = [permissions.IsAuthenticated]

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
    queryset = models.EntryFilter.objects.all().order_by("id")
    serializer_class = serializers.EntryFilterSerializer
    permission_classes = [permissions.IsAuthenticated]


class EntryFilterDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = models.EntryFilter.objects.all()
    serializer_class = serializers.EntryFilterSerializer
    permission_classes = [permissions.IsAuthenticated]


class EntryFiltersRun(generics.CreateAPIView):
    queryset = models.EntryFilter.objects.all()
    filterset_class = filters.EntryFilter
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        filtered_entries = self.filter_queryset(self.get_queryset())
        filtered_entries_ids = list(filtered_entries.values_list("pk", flat=True))
        entry_filter_ids = self.request.query_params.get("filter_ids", [])
        if entry_filter_ids:
            entry_filter_ids = map(int, entry_filter_ids.split(","))
        dispatch_task_by_name(
            TaskNamesEnum.RUN_FILTERS_ON_ENTRIES,
            kwargs={
                "entries_ids": filtered_entries_ids,
                "entry_filter_ids": entry_filter_ids,
            },
        )
        headers = self.get_success_headers([])
        return Response([], status=status.HTTP_200_OK, headers=headers)


class EntryManualAdd(generics.CreateAPIView):
    queryset = models.Entry.objects.get_annotated_queryset()
    serializer_class = serializers.EntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = serializers.EntryManualAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            new_entry = models.Entry.objects.add_entry_from_manual_channel(
                serializer.validated_data
            )
        except InvalidDataException as e:
            raise ValidationError(e.messages)
        setattr(new_entry, "published_time", new_entry._published_time)
        serializer = self.get_serializer(new_entry)
        serializer.data
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )


class ChannelsInactivate(generics.CreateAPIView):
    queryset = models.Channel.objects.get_annotated_queryset().filter(active=True)
    serializer_class = serializers.ChannelsInactivateSerializer
    filterset_class = filters.ChannelFilter
    permission_classes = [permissions.IsAuthenticated]

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
    permission_classes = [permissions.IsAuthenticated]

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


class ChannelsDelete(generics.CreateAPIView):
    queryset = models.Channel.objects.get_annotated_queryset().filter(active=False)
    serializer_class = serializers.ChannelsDeleteSerializer
    filterset_class = filters.ChannelFilter
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        keep_tagged_entries = request.data.get("keep_tagged_entries", True)
        filtered_channels = self.filter_queryset(self.get_queryset())
        deleted_channels = list(filtered_channels.values_list("pk", flat=True))
        deleted_items, deleted_count = models.Channel.objects.delete_channels(
            filtered_channels, keep_tagged_entries
        )
        serializer = self.get_serializer(
            data={
                "deleted_count": deleted_count.get("kustosz.Channel", 0),
                "deleted_channels": deleted_channels,
            }
        )
        serializer.is_valid(raise_exception=True)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)


class ChannelTagsList(generics.ListAPIView):
    queryset = models.Channel.tags.all().order_by("slug")
    serializer_class = serializers.TagsListSerializer
    permission_classes = [permissions.IsAuthenticated]


class EntryTagsList(generics.ListAPIView):
    queryset = models.Entry.tags.all().order_by("slug")
    serializer_class = serializers.TagsListSerializer
    permission_classes = [permissions.IsAuthenticated]
