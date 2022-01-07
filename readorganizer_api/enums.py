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


class InternalTasksEnum(models.TextChoices):
    ADD_READABILITY_CONTENTS = "readorganizer_api.internal.add_readability_contents"
    DEDUPLICATE_ENTRIES = "readorganizer_api.internal.deduplicate_entries"
    FETCH_FEED_CHANNEL_CONTENT = "readorganizer_api.internal.fetch_feed_channel_content"
    FETCH_MANUAL_ENTRY_DATA = "readorganizer_api.internal.fetch_manual_entry_data"
    FETCH_MANUAL_ENTRY_METADATA = (
        "readorganizer_api.internal.fetch_manual_entry_metadata"
    )
    FILTER_ACTION_RUN_SCRIPT = "readorganizer_api.internal.filter_action_run_script"
    RUN_FILTERS_ON_ENTRIES = "readorganizer_api.internal.run_filters_on_entries"
