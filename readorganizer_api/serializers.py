from rest_framework import serializers

from .models import Entry
from .models import Feed


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


class FeedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feed
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


class FeedDetailSerializer(serializers.ModelSerializer):
    entries = EntrySerializer(source="entry_set", many=True, read_only=True)

    class Meta:
        model = Feed
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
