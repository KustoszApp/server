from rest_framework import serializers

from .models import Channel
from .models import Entry


class EntrySerializer(serializers.ModelSerializer):
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
            "probable_published_time",
        ]
        extra_kwargs = {
            "id": {"read_only": True},
        }


class ChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Channel
        # FIXME: include number of unread entries
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
            "is_stale",
        ]
        extra_kwargs = {
            "id": {"read_only": True},
            "title_upstream": {"read_only": True},
            "displayed_title": {"read_only": True},
            "link": {"read_only": True},
            "last_check_time": {"read_only": True},
            "last_successful_check_time": {"read_only": True},
            "added": {"read_only": True},
            "is_stale": {"read_only": True},
        }


class ChannelDetailSerializer(serializers.ModelSerializer):
    entries = EntrySerializer(many=True, read_only=True)

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
            "is_stale",
            "entries",
        ]
        extra_kwargs = {
            "id": {"read_only": True},
            "title_upstream": {"read_only": True},
            "displayed_title": {"read_only": True},
            "link": {"read_only": True},
            "last_check_time": {"read_only": True},
            "last_successful_check_time": {"read_only": True},
            "added": {"read_only": True},
            "is_stale": {"read_only": True},
        }
