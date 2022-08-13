import logging
from collections import defaultdict
from operator import attrgetter

from django.db.models.query import QuerySet
from lxml import etree

log = logging.getLogger(__name__)


class OPMLExporter:
    def __init__(self):
        self.ungrouped = []
        self.grouped = defaultdict(list)
        self.tags = {}

    def _group_channels(self, channels: QuerySet) -> None:
        for channel in channels:
            if not channel.tags.exists():
                self.ungrouped.append(channel)
                continue

            for tag in channel.tags.all():
                self.tags[tag.slug] = tag
                self.grouped[tag.slug].append(channel)

    def _sort_groups(self) -> None:
        self.ungrouped = sorted(self.ungrouped, key=attrgetter("displayed_title"))
        sorted_groups = {}
        for group_name in sorted(self.grouped):
            group_channels = sorted(
                self.grouped.get(group_name), key=attrgetter("displayed_title")
            )
            sorted_groups[group_name] = group_channels
        self.grouped = sorted_groups

    def _create_opml_group(self, parent_etree, group_details, group_channels):
        etree_attrs = {"text": group_details.name}
        group_etree = etree.Element("outline", attrib=etree_attrs)
        for channel in group_channels:
            self._add_opml_channel(group_etree, channel)
        parent_etree.append(group_etree)

    def _add_opml_channel(self, parent_etree, channel):
        etree_attrs = {
            "text": channel.displayed_title,
            "type": "rss",
            "xmlUrl": channel.url,
            "htmlUrl": channel.link,
        }
        etree.SubElement(parent_etree, "outline", attrib=etree_attrs)

    def from_queryset(self, channels: QuerySet) -> str:
        self._group_channels(channels)
        self._sort_groups()
        exported = etree.Element("opml", attrib={"version": "2.0"})

        head = etree.SubElement(exported, "head")
        title = etree.SubElement(head, "title")
        title.text = "Your Kustosz channels [https://kustosz.org]"

        body = etree.SubElement(exported, "body")

        for group_name, group_channels in self.grouped.items():
            group_details = self.tags.get(group_name)
            self._create_opml_group(body, group_details, group_channels)
        for channel in self.ungrouped:
            self._add_opml_channel(body, channel)

        exported_content = etree.tostring(
            exported, xml_declaration=True, encoding="UTF-8", pretty_print=True
        )
        return exported_content.decode("UTF-8")
