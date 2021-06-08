from autoslug import AutoSlugField
from django.contrib.auth.models import AbstractUser
from django.db import models

from .enums import ChannelTypesEnum
from .enums import EntryContentSourceTypesEnum
from .managers import ChannelManager


class User(AbstractUser):
    pass


class Channel(models.Model):
    objects = ChannelManager()

    url = models.URLField(max_length=2048, unique=True)
    channel_type = models.CharField(max_length=20, choices=ChannelTypesEnum.choices)
    title = models.TextField(blank=True, help_text="Title (name) of channel")
    last_checked = models.DateTimeField(
        blank=True, null=True, help_text="When channel was last checked"
    )
    added = models.DateTimeField(
        auto_now_add=True, help_text="When channel was added to database"
    )
    active = models.BooleanField(
        default=True, help_text="Is this channel actively checked for new content?"
    )
    update_frequency = models.IntegerField(
        default=3600, help_text="How often channel should be checked, in seconds"
    )
    username = models.CharField(
        max_length=256,
        blank=True,
        help_text="Username for authentication (currently unused)",
    )
    password = models.CharField(
        max_length=256,
        blank=True,
        help_text="Password for authentication (currently unused)",
    )
    token = models.CharField(
        max_length=256,
        blank=True,
        help_text="Token for authentication (currently unused)",
    )

    @property
    def displayed_title(self):
        if self.title:
            return self.title

        if hasattr(self, "feed_data"):
            return self.feed_data.original_title


class ChannelFeed(models.Model):
    channel = models.OneToOneField(
        Channel, on_delete=models.CASCADE, related_name="feed_data"
    )
    original_title = models.TextField(
        blank=True, help_text="Feed title, as specified by feed itself"
    )


class Entry(models.Model):
    channel = models.ForeignKey(
        Channel, on_delete=models.CASCADE, related_name="entries"
    )
    gid = models.TextField(
        max_length=2048, unique=True, help_text="Unique identifier of entry"
    )
    url = models.URLField(max_length=2048, blank=True, help_text="URL of entry")
    title = models.TextField(blank=True, help_text="Title (subject) of entry")
    author = models.TextField(blank=True, help_text="Author of entry")
    added = models.DateTimeField(
        auto_now_add=True, help_text="When entry was added to database"
    )
    published = models.DateTimeField(
        blank=True, null=True, help_text="Publication date of entry"
    )
    archived = models.BooleanField(
        default=False, help_text="Is this entry archived (read)?"
    )
    updated = models.DateTimeField(
        blank=True, null=True, help_text="When entry was last updated in database"
    )
    updated_claim = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When entry/channel claims entry was last updated",
    )


class EntryContent(models.Model):
    entry = models.ForeignKey(
        Entry, on_delete=models.CASCADE, related_name="content_set"
    )
    source = models.CharField(
        max_length=20,
        choices=EntryContentSourceTypesEnum.choices,
        help_text="Source of this content",
    )
    content = models.TextField(help_text="Content itself")


class EntryNote(models.Model):
    entry = models.ForeignKey(Entry, on_delete=models.CASCADE, related_name="note")
    content = models.TextField()


class ChannelTag(models.Model):
    channels = models.ManyToManyField(Channel, related_name="tags")
    name = models.CharField(max_length=255, unique=True)
    slug = AutoSlugField(populate_from="name", unique=True)


class EntryTag(models.Model):
    entries = models.ManyToManyField(Entry, related_name="tags")
    name = models.CharField(max_length=255, unique=True)
    slug = AutoSlugField(populate_from="name", unique=True)
