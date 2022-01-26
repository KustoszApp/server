from celery import shared_task

from kustosz.enums import TaskNamesEnum
from kustosz.models import Entry
from kustosz.utils.run_script import run_script


@shared_task(name=TaskNamesEnum.FILTER_ACTION_RUN_SCRIPT)
def filter_action_run_script(entry_id: int, script_path):
    entry = Entry.objects.prefetch_related("channel", "tags").get(pk=entry_id)
    run_script(entry, script_path)
