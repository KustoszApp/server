import logging
from collections import defaultdict

from django.db.models.query import QuerySet

from . import normalize_url

log = logging.getLogger(__name__)


class DuplicateFinder:
    def __init__(self):
        self.results = defaultdict(set)
        self.processors = (
            self.get_gid,
            self.get_normalized_link,
            self.get_author_title,
        )

    def get_gid(self, entry) -> str:
        return entry.gid

    def get_normalized_link(self, entry) -> str:
        return normalize_url(entry.link)

    def get_author_title(self, entry) -> str:
        return f"{entry.author} {entry.title}"

    def find_in(self, entries: QuerySet) -> tuple[int, ...]:
        found_duplicates = []
        for entry in entries.order_by("added_time"):
            for function in self.processors:
                function_name = function.__qualname__
                function_results = self.results[function_name]
                result = function(entry)
                if result not in function_results:
                    function_results.add(result)
                    continue
                if entry.archived is True:
                    continue
                log.info(
                    "Entry %s (%s) is considered a duplicate based on %s call result",
                    entry.pk,
                    entry.gid,
                    function_name,
                )
                found_duplicates.append(entry.pk)
                break
        return tuple(found_duplicates)
