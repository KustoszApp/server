from celery import chain
from celery import shared_task

from .task_add_readability_contents import add_readability_contents
from .task_fetch_manual_entry_metadata import fetch_manual_entry_metadata
from readorganizer_api.enums import InternalTasksEnum


@shared_task(name=InternalTasksEnum.FETCH_MANUAL_ENTRY_DATA)
def fetch_manual_entry_data(entry_id: int):
    tasks_chain = chain(
        fetch_manual_entry_metadata.si(entry_id), add_readability_contents.si(entry_id)
    )
    tasks_chain.apply_async()
