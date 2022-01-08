from django.db import models


class ChannelTypesEnum(models.TextChoices):
    MANUAL = "manual", "Manual"
    FEED = "feed", "RSS/Atom feed"


class EntryContentSourceTypesEnum(models.TextChoices):
    FEED_SUMMARY = "summary", "Feed - summary field"
    FEED_CONTENT = "content", "Feed - content field"
    READABILITY = "readability", "Readability (Python implementation)"
    NODE_READABILITY = "nodereadability", "Readability (Node.js implementation)"


class EntryFilterActionsEnum(models.TextChoices):
    DO_NOTHING = "nothing", "Do nothing"
    MARK_AS_READ = "mark_as_read", "Mark as read"
    ASSIGN_TAG = "assign_tag", "Assign tag"
    RUN_SCRIPT = "run_script", "Run external application"


class ImportChannelsActionsEnum(models.TextChoices):
    AUTODISCOVER = "autodiscover"
    OPML = "opml"
    CONFIG = "config"


class TaskNamesEnum(models.TextChoices):
    ADD_CHANNELS = "readorganizer.add_channels"
    ADD_READABILITY_CONTENTS = "readorganizer.add_readability_contents"
    DEDUPLICATE_ENTRIES = "readorganizer.deduplicate_entries"
    FETCH_CHANNEL_CONTENT = "readorganizer.fetch_channel_content"
    FETCH_FEED_CHANNEL_CONTENT = "readorganizer.fetch_feed_channel_content"
    FETCH_MANUAL_ENTRY_DATA = "readorganizer.fetch_manual_entry_data"
    FETCH_MANUAL_ENTRY_METADATA = "readorganizer.fetch_manual_entry_metadata"
    FILTER_ACTION_RUN_SCRIPT = "readorganizer.filter_action_run_script"
    RUN_FILTERS_ON_ENTRIES = "readorganizer.run_filters_on_entries"
