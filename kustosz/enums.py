from django.db import models


class AsyncTaskStatesEnum(models.TextChoices):
    IN_PROGRESS = "in_progress", "In progress"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


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


class SerialQueuesNamesEnum(models.TextChoices):
    FEED_FETCHER = "feed_fetcher"


class TaskNamesEnum(models.TextChoices):
    ADD_CHANNELS = "kustosz.add_channels"
    ADD_READABILITY_CONTENTS = "kustosz.add_readability_contents"
    AUTODETECT_CONTENT_FROM_URL = "kustosz.autodetect_content_from_url"
    AUTODETECT_CHANNEL_CONTENT_FROM_URL = "kustosz.autodetect_channel_content_from_url"
    AUTODETECT_CHANNELS_FROM_URL = "kustosz.autodetect_channels_from_url"
    AUTODETECT_ENTRY_CONTENT_FROM_URL = "kustosz.autodetect_entry_content_from_url"
    CLEAN_FEED_FETCHER_CACHE = "kustosz.clean_feed_fetcher_cache"
    CLEAN_URL_FETCHER_CACHE = "kustosz.clean_url_fetcher_cache"
    DEDUPLICATE_ENTRIES = "kustosz.deduplicate_entries"
    FETCH_CHANNEL_CONTENT = "kustosz.fetch_channel_content"
    FETCH_FEED_CHANNEL_CONTENT = "kustosz.fetch_feed_channel_content"
    FETCH_MANUAL_ENTRY_DATA = "kustosz.fetch_manual_entry_data"
    FETCH_MANUAL_ENTRY_METADATA = "kustosz.fetch_manual_entry_metadata"
    FILTER_ACTION_RUN_SCRIPT = "kustosz.filter_action_run_script"
    RUN_FILTERS_ON_ENTRIES = "kustosz.run_filters_on_entries"
