from django.utils.timezone import now as django_now
from rest_framework import serializers
from taggit.models import Tag
from taggit_serializer.serializers import TaggitSerializer
from taggit_serializer.serializers import TagListSerializerField

from .models import Channel
from .models import Entry
from .models import EntryContent
from .models import EntryFilter


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
    published_time = serializers.DateTimeField()
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
            "added_time",
            "updated_time",
            "published_time_upstream",
            "updated_time_upstream",
            "published_time",
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
            "published_time": {"read_only": True},
        }

    def update(self, instance, validated_data):
        instance.updated_time = django_now()
        return super().update(instance, validated_data)


class EntriesArchiveSerializer(serializers.Serializer):
    archived_entries = serializers.ListField(
        child=serializers.IntegerField(), required=True
    )
    archived_count = serializers.IntegerField(required=True)


class EntryFilterSerializer(serializers.Serializer):
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


class TagsListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = [
            "name",
            "slug",
        ]
