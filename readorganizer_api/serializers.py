from django.utils.timezone import now as django_now
from rest_framework import exceptions
from rest_framework import fields as drf_fields
from rest_framework import serializers
from taggit.models import Tag
from taggit_serializer.serializers import TaggitSerializer
from taggit_serializer.serializers import TagListSerializerField

from .constants import MANUAL_CHANNEL_ID
from .exceptions import InvalidDataException
from .models import Channel
from .models import Entry
from .models import EntryContent
from .models import EntryFilter
from .types import EntryDataInput


class EntryContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EntryContent
        fields = [
            "source",
            "content",
            "mimetype",
            "language",
            "estimated_reading_time",
            "updated_time",
        ]


class EntryContentMetadataSerializer(EntryContentSerializer):
    class Meta(EntryContentSerializer.Meta):
        fields = [
            "source",
            "mimetype",
            "language",
            "estimated_reading_time",
            "updated_time",
        ]


class EntryContentNestedWritableSerializer(EntryContentSerializer):
    def run_validation(self, data):
        method = self.parent.context.get("request").method
        if data is not drf_fields.empty and method == "PATCH":
            for key in ("source", "mimetype", "language"):
                if key not in data:
                    msg = f'"{key}" is mandatory'
                    raise exceptions.ValidationError(msg)
        return super().run_validation(data=data)


class EntriesListSerializer(serializers.ModelSerializer):
    published_time = serializers.DateTimeField()
    preferred_content = EntryContentSerializer()
    available_contents = EntryContentMetadataSerializer(source="content_set", many=True)

    class Meta:
        model = Entry
        fields = [
            "id",
            "channel",
            "gid",
            "archived",
            "link",
            "title",
            "author",
            "reader_position",
            "added_time",
            "updated_time",
            "published_time_upstream",
            "updated_time_upstream",
            "published_time",
            "preferred_content",
            "available_contents",
        ]
        extra_kwargs = {
            "id": {"read_only": True},
        }


class EntrySerializer(TaggitSerializer, serializers.ModelSerializer):
    published_time = serializers.DateTimeField(read_only=True)
    preferred_content = EntryContentNestedWritableSerializer()
    contents = EntryContentSerializer(source="content_set", required=False, many=True)
    tags = TagListSerializerField()

    class Meta:
        model = Entry
        fields = [
            "id",
            "channel",
            "gid",
            "archived",
            "link",
            "title",
            "author",
            "note",
            "reader_position",
            "added_time",
            "updated_time",
            "published_time_upstream",
            "updated_time_upstream",
            "published_time",
            "preferred_content",
            "contents",
            "tags",
        ]
        extra_kwargs = {
            "id": {"read_only": True},
            "channel": {"read_only": True},
            "gid": {"read_only": True},
            "link": {"read_only": True},
            "title": {"read_only": True},
            "author": {"read_only": True},
            "added_time": {"read_only": True},
            "updated_time": {"read_only": True},
            "published_time_upstream": {"read_only": True},
            "updated_time_upstream": {"read_only": True},
        }

    def update(self, instance, validated_data):
        new_preferred_content = validated_data.pop("preferred_content", None)
        if new_preferred_content:
            try:
                instance.set_new_preferred_content(new_preferred_content)
            except InvalidDataException as e:
                raise exceptions.ValidationError(e.message)
        instance.updated_time = django_now()
        return super().update(instance, validated_data)


class EntriesArchiveSerializer(serializers.Serializer):
    archived_entries = serializers.ListField(
        child=serializers.IntegerField(), required=True
    )
    archived_count = serializers.IntegerField(required=True)


class EntryFilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = EntryFilter
        fields = [
            "id",
            "enabled",
            "name",
            "condition",
            "action_name",
            "action_argument",
        ]
        extra_kwargs = {
            "id": {"read_only": True},
        }


class ChannelsListSerializer(serializers.ModelSerializer):
    unarchived_entries = serializers.IntegerField()
    last_entry_published_time = serializers.DateTimeField()
    tags = TagListSerializerField()

    class Meta:
        model = Channel
        fields = [
            "id",
            "url",
            "title",
            "active",
            "update_frequency",
            "title_upstream",
            "displayed_title",
            "link",
            "last_check_time",
            "last_successful_check_time",
            "added_time",
            "deduplication_enabled",
            "is_stale",
            "unarchived_entries",
            "last_entry_published_time",
            "tags",
        ]
        extra_kwargs = {
            "id": {"read_only": True},
            "title_upstream": {"read_only": True},
            "displayed_title": {"read_only": True},
            "link": {"read_only": True},
            "last_check_time": {"read_only": True},
            "last_successful_check_time": {"read_only": True},
            "added_time": {"read_only": True},
            "is_stale": {"read_only": True},
            "unarchived_entries": {"read_only": True},
            "last_entry_published_time": {"read_only": True},
        }


class ChannelSerializer(TaggitSerializer, serializers.ModelSerializer):
    unarchived_entries = serializers.IntegerField()
    last_entry_published_time = serializers.DateTimeField()
    tags = TagListSerializerField()

    class Meta:
        model = Channel
        fields = [
            "id",
            "url",
            "title",
            "title_upstream",
            "displayed_title",
            "link",
            "last_check_time",
            "last_successful_check_time",
            "added_time",
            "active",
            "update_frequency",
            "deduplication_enabled",
            "is_stale",
            "unarchived_entries",
            "last_entry_published_time",
            "tags",
        ]
        extra_kwargs = {
            "id": {"read_only": True},
            "title_upstream": {"read_only": True},
            "displayed_title": {"read_only": True},
            "link": {"read_only": True},
            "last_check_time": {"read_only": True},
            "last_successful_check_time": {"read_only": True},
            "added_time": {"read_only": True},
            "is_stale": {"read_only": True},
            "unarchived_entries": {"read_only": True},
            "last_entry_published_time": {"read_only": True},
        }


class ChannelsInactivateSerializer(serializers.Serializer):
    inactivated_channels = serializers.ListField(
        child=serializers.IntegerField(), required=True
    )
    inactivated_count = serializers.IntegerField(required=True)


class ChannelsActivateSerializer(serializers.Serializer):
    activated_channels = serializers.ListField(
        child=serializers.IntegerField(), required=True
    )
    activated_count = serializers.IntegerField(required=True)


class EntryManualAddSerializer(TaggitSerializer, serializers.Serializer):
    link = serializers.URLField()
    title = serializers.CharField(required=False)
    author = serializers.CharField(required=False)
    published_time = serializers.DateTimeField(required=False)
    updated_time = serializers.DateTimeField(required=False)
    tags = TagListSerializerField(required=False)

    def to_internal_value(self, data):
        internal_value = super().to_internal_value(data)
        return EntryDataInput(channel=MANUAL_CHANNEL_ID, **internal_value)


class TagsListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = [
            "name",
            "slug",
        ]
