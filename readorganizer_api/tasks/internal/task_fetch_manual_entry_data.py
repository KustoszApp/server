from celery import shared_task

from readorganizer_api.enums import InternalTasksEnum


@shared_task(name=InternalTasksEnum.FETCH_MANUAL_ENTRY_DATA)
def fetch_manual_entry_data(entry_id: int):
    # FIXME: this is stub
    pass
