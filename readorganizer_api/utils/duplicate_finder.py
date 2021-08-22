import logging
from collections import defaultdict

from django.db.models.query import QuerySet

from . import normalize_url

log = logging.getLogger(__name__)


class DuplicateFinder:
    def __init__(self):
        self.results = defaultdict(lambda: defaultdict(set))
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

    def seen_values_except_channel(self, function_name, channel_id):
        all_values = set()
        for channel, results_store in self.results.items():
            if channel == channel_id:
                continue
            for fn_name, values in results_store.items():
                if fn_name == function_name:
                    all_values.update(values)
        return all_values

    def is_duplicate(self, entry, function):
        function_name = function.__qualname__
        channel_id = entry.channel.pk
        seen_values = self.seen_values_except_channel(function_name, channel_id)
        function_result = function(entry)
        duplicate = function_result in seen_values
        self.results[channel_id][function_name].add(function_result)
        return duplicate

    def find_in(self, entries: QuerySet) -> tuple[int, ...]:
        found_duplicates = []
        for entry in entries.select_related("channel").order_by("added_time"):
            for function in self.processors:
                function_name = function.__qualname__
                is_duplicate = self.is_duplicate(entry, function)
                if entry.archived is True or not is_duplicate:
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
