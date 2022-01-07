from celery import shared_task

from readorganizer_api.enums import InternalTasksEnum
from readorganizer_api.models import Entry
from readorganizer_api.utils.run_script import run_script


@shared_task(name=InternalTasksEnum.FILTER_ACTION_RUN_SCRIPT)
def filter_action_run_script(entry_id: int, script_path):
    entry = Entry.objects.prefetch_related("channel", "tags").get(pk=entry_id)
    run_script(entry, script_path)
