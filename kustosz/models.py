from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import MultipleObjectsReturned
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.timezone import now as django_now
from taggit.managers import TaggableManager

from .constants import DEFAULT_ENTRY_OPEN_READ_TIMEOUT
from .constants import DEFAULT_UPDATE_FREQUENCY
from .enums import ChannelTypesEnum
from .enums import EntryContentSourceTypesEnum
from .enums import EntryFilterActionsEnum
from .exceptions import InvalidDataException
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
    default_filter = models.TextField(
        blank=True,
        help_text="Entry search filter definition used by default on entries view",
    )
    theme_color = models.TextField(blank=True, help_text="User preferred color theme")
    theme_view = models.TextField(blank=True, help_text="User preferred view")
    entry_open_read_timeout = models.IntegerField(
        default=DEFAULT_ENTRY_OPEN_READ_TIMEOUT,
        help_text="When after opening entry it should be marked as read (in seconds)",
    )
    entry_open_scroll_to_top = models.BooleanField(
        default=True,
        help_text="Should entry scroll to top automatically after opening?",
    )


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
    deduplication_enabled = models.BooleanField(
        default=True,
        help_text="Is new content from this channel subject to deduplication?",
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
    note = models.TextField(blank=True, help_text="Note associated with entry")
    reader_position = models.FloatField(
        blank=True,
        default=0,
        help_text=(
            "Last position of reader viewport, as percentage; "
            "enables clients to implement 'continue reading' functionality"
        ),
    )
    selected_preferred_content = models.ForeignKey(
        "EntryContent",
        on_delete=models.SET_NULL,
        related_name="preferred_content_for",
        null=True,
        blank=True,
        default=None,
        help_text="Last entry content selected by user",
    )
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
    readability_fetch_time = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When did we fetch readability content for entry",
    )

    class Meta:
        verbose_name_plural = "entries"
        constraints = [
            models.UniqueConstraint(
                fields=["channel", "gid"], name="unique_channel_gid"
            )
        ]

    def set_new_preferred_content(self, new_preferred_content):
        try:
            found_content = self.content_set.get(pk=new_preferred_content.id)
        except ObjectDoesNotExist:
            msg = "Could not find content matching provided criteria"
            raise InvalidDataException(msg)
        except MultipleObjectsReturned:
            msg = "Multiple content objects match provided criteria"
            raise InvalidDataException(msg)
        self.selected_preferred_content = found_content

    @property
    def _published_time(self):
        if self.published_time_upstream:
            return self.published_time_upstream
        if self.updated_time_upstream:
            return self.updated_time_upstream

    @property
    def preferred_content(self):
        if self.selected_preferred_content:
            return self.selected_preferred_content
        return self.content_set.order_by("-estimated_reading_time").first()


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
    estimated_reading_time = models.FloatField(
        blank=True, help_text="Estimated read time, in minutes"
    )
    updated_time = models.DateTimeField(help_text="When content was last updated")


class EntryFilter(models.Model):
    enabled = models.BooleanField(
        default=True, help_text="Is this filtering rule enabled?"
    )
    name = models.TextField(blank=False, help_text="Name of the filtering rule")
    condition = models.TextField(
        blank=False, help_text="Condition to match entries (as filterset definition)"
    )
    action_name = models.CharField(
        max_length=20, blank=False, choices=EntryFilterActionsEnum.choices
    )
    action_argument = models.TextField(
        blank=True, help_text="Argument to action (name of tag, path to script etc.)"
    )

    def clean(self):
        actions_without_args = (EntryFilterActionsEnum.MARK_AS_READ,)
        if self.action_name not in actions_without_args and not self.action_argument:
            msg = f"Action {self.action_name} requires action_argument"
            raise InvalidDataException({"action_argument": msg})
