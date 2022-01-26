from celery import shared_task
from django.conf import settings

from kustosz.enums import TaskNamesEnum
from kustosz.exceptions import TransientFetcherError
from kustosz.models import Entry


@shared_task(
    name=TaskNamesEnum.FETCH_MANUAL_ENTRY_METADATA,
    autoretry_for=(TransientFetcherError,),
    retry_kwargs={"max_retries": settings.KUSTOSZ_FETCH_PAGE_MAX_RETRIES},
    retry_backoff=5,
    retry_jitter=False,
)
def fetch_manual_entry_metadata(entry_id: int):
    Entry.objects._ensure_manual_entry_metadata(entry_id)
