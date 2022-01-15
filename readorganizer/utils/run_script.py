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
    log.info(
        "Running script %s on entry %s [entry gid: %s]",
        script_path,
        entry.pk,
        entry.gid,
    )
    cp = subprocess.run(
        script_path,
        encoding="UTF-8",
        env=entry_data_env(entry),
        capture_output=True,
        text=True,
        timeout=30,
    )

    if cp.stdout:
        log.debug(
            "Script %s entry %s standard output: %s", script_path, entry.pk, cp.stdout
        )

    if cp.stderr:
        log.warning(
            "Script %s entry %s standard error: %s", script_path, entry.pk, cp.stderr
        )

    log.info(
        "Finished running script %s on entry %s. Exit code: %s",
        script_path,
        entry.pk,
        cp.returncode,
    )
