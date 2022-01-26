from django.utils.timezone import now as django_now

from kustosz.enums import EntryFilterActionsEnum
from kustosz.enums import TaskNamesEnum
from kustosz.utils import dispatch_task_by_name


def do_nothing(filtered_entries, *args):
    pass


def mark_as_read(filtered_entries, *args):
    filtered_entries.update(archived=True, updated_time=django_now())


def assign_tag(filtered_entries, tag_name):
    # TODO: adding multiple tags?
    for entry in filtered_entries:
        entry.tags.add(tag_name)


def run_script(filtered_entries, script_path):
    for entry in filtered_entries:
        dispatch_task_by_name(
            TaskNamesEnum.FILTER_ACTION_RUN_SCRIPT,
            kwargs={"entry_id": entry.pk, "script_path": script_path},
        )


def get_filter_action(action_name: str):
    if action_name == EntryFilterActionsEnum.MARK_AS_READ:
        return mark_as_read
    elif action_name == EntryFilterActionsEnum.ASSIGN_TAG:
        return assign_tag
    elif action_name == EntryFilterActionsEnum.RUN_SCRIPT:
        return run_script
    else:
        return do_nothing
