from rest_framework import serializers

from .models import Channel
from .models import Entry


class EntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Entry
        fields = [
            "id",
            "feed",
            "title",
            "link",
            "updated",
            "author",
            "published",
            "read",
        ]
        extra_kwargs = {
            "id": {"read_only": True},
        }


class ChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Channel
        fields = [
            "id",
            "url",
            "title",
            "last_checked",
            "added",
            "active",
            "update_frequency",
        ]
        extra_kwargs = {
            "id": {"read_only": True},
        }


class ChannelDetailSerializer(serializers.ModelSerializer):
    entries = EntrySerializer(source="entry_set", many=True, read_only=True)

    class Meta:
        model = Channel
        fields = [
            "id",
            "url",
            "title",
            "last_checked",
            "added",
            "active",
            "update_frequency",
            "entries",
        ]
        extra_kwargs = {
            "id": {"read_only": True},
        }
