from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings

from kustosz.enums import TaskNamesEnum
from kustosz.models import Entry


logger = get_task_logger(__name__)


@shared_task(name=TaskNamesEnum.DEDUPLICATE_ENTRIES)
def deduplicate_entries(
    days: int = settings.KUSTOSZ_DEDUPLICATE_DAYS,
) -> tuple[int, ...]:
    return_value = Entry.objects.deduplicate_entries(days)
    return return_value
