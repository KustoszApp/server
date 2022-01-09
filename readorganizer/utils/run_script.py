import logging
import os
import subprocess


log = logging.getLogger(__name__)


def entry_data_env(entry):
    env_namespace = "READORGANIZER_"
    new_env = os.environ.copy()
    entry_keys = (
        "id",
        "gid",
        "archived",
        "link",
        "title",
        "author",
        "added_time",
        "updated_time",
        "published_time_upstream",
        "updated_time_upstream",
    )
    channel_keys = (
        "id",
        "url",
        "channel_type",
        "title",
        "title_upstream",
        "link",
        "last_check_time",
        "last_successful_check_time",
        "added_time",
        "active",
        "update_frequency",
        "deduplication_enabled",
        "displayed_title",
    )

    for key in entry_keys:
        key_name = f"{env_namespace}{key.upper()}"
        value = str(getattr(entry, key))
        new_env[key_name] = value

    for key in channel_keys:
        key_name = f"{env_namespace}CHANNEL_{key.upper()}"
        value = str(getattr(entry.channel, key))
        new_env[key_name] = value

    new_env[f"{env_namespace}TAGS"] = ",".join(entry.tags.slugs())
    new_env[f"{env_namespace}CHANNEL_TAGS"] = ",".join(entry.channel.tags.slugs())
    return new_env


def run_script(entry, script_path):
    cp = subprocess.run(
        script_path,
        encoding="UTF-8",
        env=entry_data_env(entry),
        capture_output=True,
        text=True,
        timeout=30,
    )

    log.info(
        "Finished running script %s, entry %s. Exit code: %s",
        script_path,
        entry.pk,
        cp.returncode,
    )

    if cp.stdout:
        log.info(
            "Script %s, entry %s standard output: %s", script_path, entry.pk, cp.stdout
        )

    if cp.stderr:
        log.info(
            "Script %s, entry %s standard error: %s", script_path, entry.pk, cp.stderr
        )
