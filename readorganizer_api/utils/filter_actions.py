from django.utils.timezone import now as django_now

from readorganizer_api.enums import EntryFilterActionsEnum


def do_nothing(filtered_entries, *args):
    pass


def mark_as_read(filtered_entries, *args):
    filtered_entries.update(archived=True, updated_time=django_now())


def assign_tag(filtered_entries, tag_name):
    # TODO: adding multiple tags?
    for entry in filtered_entries:
        entry.tags.add(tag_name)


def get_filter_action(action_name: str):
    if action_name == EntryFilterActionsEnum.MARK_AS_READ:
        return mark_as_read
    elif action_name == EntryFilterActionsEnum.ASSIGN_TAG:
        return assign_tag
    else:
        return do_nothing
