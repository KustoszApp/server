from typing import Iterable

from celery import shared_task

from readorganizer.enums import TaskNamesEnum
from readorganizer.models import Entry
from readorganizer.models import EntryFilter


@shared_task(name=TaskNamesEnum.RUN_FILTERS_ON_ENTRIES)
def run_filters_on_entries(
    entries_ids: Iterable[int], entry_filter_ids: Iterable[int] = None
):
    entry_filters = EntryFilter.objects.all()
    if entry_filter_ids:
        entry_filters = EntryFilter.objects.filter(pk__in=entry_filter_ids)
    Entry.objects._run_filters_on_entries(entries_ids, entry_filters)
