from django.utils.timezone import now as django_now
from rest_framework import exceptions
from rest_framework import serializers
from taggit.models import Tag

from .enums import AsyncTaskStatesEnum
from .enums import ChannelTypesEnum
from .enums import EntryFilterActionsEnum
from .exceptions import InvalidDataException
from .models import Channel
from .models import Entry
from .models import EntryContent
from .models import EntryFilter
from .models import User
from .third_party.taggit_serializer.serializers import TaggitSerializer
from .third_party.taggit_serializer.serializers import TagListSerializerField
from .types import EntryDataInput
from .validators import ChannelURLValidator


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "username",
            "is_active",
            "date_joined",
            "default_filter",
            "theme_color",
            "theme_view",
            "entry_open_read_timeout",
            "entry_open_scroll_to_top",
        ]
        extra_kwargs = {
            "username": {"read_only": True},
            "is_active": {"read_only": True},
            "date_joined": {"read_only": True},
        }


class EntryContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EntryContent
        fields = [
            "id",
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
            "id",
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
            "reader_position",
            "added_time",
            "updated_time",
            "published_time_upstream",
            "updated_time_upstream",
            "published_time",
            "preferred_content",
            "available_contents",
            "tags",
        ]
        extra_kwargs = {
            "id": {"read_only": True},
        }


class EntrySerializer(TaggitSerializer, serializers.ModelSerializer):
    published_time = serializers.DateTimeField(read_only=True)
    preferred_content = EntryContentSerializer()
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

    def to_internal_value(self, data):
        self.fields["preferred_content"] = serializers.PrimaryKeyRelatedField(
            queryset=EntryContent.objects.all()
        )
        return super().to_internal_value(data)

    def to_representation(self, obj):
        self.fields["preferred_content"] = EntryContentSerializer()
        return super().to_representation(obj)

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

    def validate(self, data):
        actions_without_args = (EntryFilterActionsEnum.MARK_AS_READ,)
        if (
            "action_name" in data
            and data.get("action_name") not in actions_without_args
            and not data.get("action_argument")
        ):
            raise serializers.ValidationError(
                f'Action {data["action_name"]} requires action_argument'
            )
        return data


class ChannelSerializer(TaggitSerializer, serializers.ModelSerializer):
    unarchived_entries = serializers.IntegerField(read_only=True)
    tagged_entries = serializers.IntegerField(read_only=True)
    total_entries = serializers.IntegerField(read_only=True)
    last_entry_published_time = serializers.DateTimeField(read_only=True)
    tags = TagListSerializerField(required=False)

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
            "tagged_entries",
            "total_entries",
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


class ChannelsDeleteSerializer(serializers.Serializer):
    deleted_channels = serializers.ListField(
        child=serializers.IntegerField(), required=True
    )
    deleted_count = serializers.IntegerField(required=True)


class EntryManualAddSerializer(TaggitSerializer, serializers.Serializer):
    link = serializers.URLField()
    title = serializers.CharField(required=False)
    author = serializers.CharField(required=False)
    published_time = serializers.DateTimeField(required=False)
    updated_time = serializers.DateTimeField(required=False)
    tags = TagListSerializerField(required=False)

    def to_internal_value(self, data):
        internal_value = super().to_internal_value(data)
        manual_channel = Channel.objects.get(channel_type=ChannelTypesEnum.MANUAL)
        return EntryDataInput(channel=manual_channel.pk, **internal_value)


class TagsListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = [
            "name",
            "slug",
        ]


class AutodetectedEntrySerializer(serializers.Serializer):
    gid = serializers.CharField(read_only=True)
    link = serializers.URLField(read_only=True)
    title = serializers.CharField(read_only=True)
    author = serializers.CharField(read_only=True)
    published_time_upstream = serializers.DateTimeField(read_only=True)
    updated_time_upstream = serializers.DateTimeField(read_only=True)
    published_time = serializers.DateTimeField(read_only=True)


class AutodetectedChannelSerializer(serializers.Serializer):
    url = serializers.CharField(read_only=True)
    title_upstream = serializers.CharField(read_only=True)
    link = serializers.CharField(read_only=True)
    total_entries = serializers.IntegerField(read_only=True)
    last_entry_published_time = serializers.DateTimeField(read_only=True)
    entries = serializers.ListField(child=AutodetectedEntrySerializer(), read_only=True)


class AutodetectAddSerializer(serializers.Serializer):
    url = serializers.URLField(
        write_only=True, required=True, validators=[ChannelURLValidator]
    )
    state = serializers.ChoiceField(
        choices=AsyncTaskStatesEnum.choices, read_only=True, allow_blank=False
    )
    entries = serializers.ListField(child=AutodetectedEntrySerializer(), read_only=True)
    channels = serializers.ListField(
        child=AutodetectedChannelSerializer(), read_only=True
    )
