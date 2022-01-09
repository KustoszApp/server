from celery import shared_task
from django.conf import settings

from readorganizer.enums import TaskNamesEnum
from readorganizer.exceptions import TransientFetcherError
from readorganizer.models import Entry


@shared_task(
    name=TaskNamesEnum.FETCH_MANUAL_ENTRY_METADATA,
    autoretry_for=(TransientFetcherError,),
    retry_kwargs={"max_retries": settings.READORGANIZER_FETCH_PAGE_MAX_RETRIES},
    retry_backoff=5,
    retry_jitter=False,
)
def fetch_manual_entry_metadata(entry_id: int):
    Entry.objects._ensure_manual_entry_metadata(entry_id)
