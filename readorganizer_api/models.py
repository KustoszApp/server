from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.timezone import now as django_now
from taggit.managers import TaggableManager

from .constants import DEFAULT_UPDATE_FREQUENCY
from .enums import ChannelTypesEnum
from .enums import EntryContentSourceTypesEnum
from .forms.fields import ChannelURLFormField
from .managers import ChannelManager
from .managers import EntryManager
from .validators import ChannelURLValidator


class ChannelURLField(models.URLField):
    default_validators = [ChannelURLValidator()]

    def formfield(self, **kwargs):
        return super().formfield(
            **{
                "form_class": ChannelURLFormField,
            }
        )


class User(AbstractUser):
    pass


class Channel(models.Model):
    objects = ChannelManager()

    tags = TaggableManager()

    url = ChannelURLField(max_length=2048, unique=True)
    channel_type = models.CharField(max_length=20, choices=ChannelTypesEnum.choices)
    title = models.TextField(blank=True, help_text="Title (name) of channel")
    title_upstream = models.TextField(
        blank=True, help_text="Channel title, as specified by channel itself"
    )
    link = models.TextField(
        blank=True,
        help_text="Channel link attribute, e.g. URL of content index in HTML format",
    )
    last_check_time = models.DateTimeField(
        blank=True, null=True, help_text="When channel was last checked"
    )
    last_successful_check_time = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When last check of channel did not result in error",
    )
    added_time = models.DateTimeField(
        auto_now_add=True, help_text="When channel was added to database"
    )
    active = models.BooleanField(
        default=True, help_text="Is this channel actively checked for new content?"
    )
    update_frequency = models.IntegerField(
        default=DEFAULT_UPDATE_FREQUENCY,
        help_text="How often channel should be checked, in seconds",
    )

    @property
    def displayed_title(self):
        if self.title:
            return self.title
        else:
            return self.title_upstream

    @property
    def is_stale(self):
        if not self.last_check_time:
            return False

        last_successful_check = self.last_successful_check_time or self.added_time

        # last 10 checks
        frequency_staleness_seconds = self.update_frequency * 10
        # last three days
        date_staleness_seconds = 3 * 24 * 60 * 60
        staleness_seconds = max(frequency_staleness_seconds, date_staleness_seconds)
        staleness_line = django_now() - timedelta(seconds=staleness_seconds)

        return staleness_line > last_successful_check


class Entry(models.Model):
    objects = EntryManager()

    tags = TaggableManager()

    channel = models.ForeignKey(
        Channel, on_delete=models.CASCADE, related_name="entries"
    )
    gid = models.TextField(max_length=2048, help_text="Unique identifier of entry")
    archived = models.BooleanField(
        default=False, help_text="Is this entry archived (read)?"
    )
    link = models.URLField(max_length=2048, blank=True, help_text="URL of entry")
    title = models.TextField(blank=True, help_text="Title (subject) of entry")
    author = models.TextField(blank=True, help_text="Author of entry")
    added_time = models.DateTimeField(
        auto_now_add=True, help_text="When entry was added to database"
    )
    updated_time = models.DateTimeField(
        blank=True, null=True, help_text="When entry was last updated in database"
    )
    published_time_upstream = models.DateTimeField(
        blank=True, null=True, help_text="Publication date of entry"
    )
    updated_time_upstream = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When entry/channel claims entry was last updated",
    )

    class Meta:
        verbose_name_plural = "entries"
        constraints = [
            models.UniqueConstraint(
                fields=["channel", "gid"], name="unique_channel_gid"
            )
        ]

    @property
    def _published_time(self):
        if self.published_time_upstream:
            return self.published_time_upstream
        if self.updated_time_upstream:
            return self.updated_time_upstream

    @property
    def preferred_content(self):
        return self.content_set.last()


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
    mimetype = models.TextField(blank=True, help_text="Type of content")
    language = models.TextField(blank=True, help_text="Language of content")
    updated_time = models.DateTimeField(help_text="When content was last updated")


class EntryNote(models.Model):
    entry = models.ForeignKey(Entry, on_delete=models.CASCADE, related_name="note")
    content = models.TextField()
