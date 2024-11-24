import json
import logging
import subprocess
from typing import Optional

from django.conf import settings
from readability import Document
from readability.readability import Unparseable
from requests import Response

from kustosz.enums import EntryContentSourceTypesEnum
from kustosz.types import FetchedFeedEntryContent
from kustosz.types import ReadabilityContentList


log = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = ("text/html", "application/xml")


class ReadabilityContentExtractor:
    def _get_python_readability(
        self, response: Response
    ) -> Optional[FetchedFeedEntryContent]:
        doc = Document(response.text)
        try:
            extracted_content = doc.summary(html_partial=True)
        except Unparseable:
            return None
        return FetchedFeedEntryContent(
            source=EntryContentSourceTypesEnum.READABILITY,
            content=extracted_content,
            mimetype="text/html",
        )

    def _get_node_readability(
        self, response: Response
    ) -> Optional[FetchedFeedEntryContent]:
        node_readability_input = {
            "html": response.text,
            "url": response.url,
        }
        try:
            cp = subprocess.run(
                settings.KUSTOSZ_READABILITY_NODE_EXECUTABLE,
                input=json.dumps(node_readability_input),
                encoding="UTF-8",
                capture_output=True,
                text=True,
                timeout=10,
            )
        except FileNotFoundError:
            log.warning("node readability script could not be run", exc_info=True)
            return None
        except subprocess.TimeoutExpired:
            log.warning(
                "node readability script did not complete within specified time",
                exc_info=True,
            )
            return None

        if cp.stderr:
            log.warning("node readability script failed:\n%s", cp.stderr)
            return None

        if cp.returncode:
            log.warning(
                "node readability script returned error code: %s", cp.returncode
            )
            return None

        try:
            readability_data = json.loads(cp.stdout)
        except json.JSONDecodeError:
            log.warning("could not parse node readability script output", exc_info=True)
            return None

        if not readability_data:
            log.warning("node readability script did not return anything")
            return None

        extracted_content = readability_data.get("content", None)
        if not extracted_content:
            log.warning(
                (
                    "node readability did not return `content` property, "
                    "or `content` is empty"
                )
            )
            return None

        return FetchedFeedEntryContent(
            source=EntryContentSourceTypesEnum.NODE_READABILITY,
            content=extracted_content,
            mimetype="text/html",
        )

    def _from_response(self, response: Response) -> ReadabilityContentList:
        obtained_content = []
        content_type = response.headers.get("Content-Type", "")
        if not (
            response.text.strip()
            and any(_type in content_type for _type in ALLOWED_CONTENT_TYPES)
        ):
            return ReadabilityContentList(content=tuple(obtained_content))

        if settings.KUSTOSZ_READABILITY_PYTHON_ENABLED:
            content = self._get_python_readability(response)
            if content:
                obtained_content.append(content)

        if settings.KUSTOSZ_READABILITY_NODE_ENABLED:
            content = self._get_node_readability(response)
            if content:
                obtained_content.append(content)

        return ReadabilityContentList(content=tuple(obtained_content))

    @classmethod
    def from_response(cls, response: Response) -> ReadabilityContentList:
        extractor = cls()
        new_content = extractor._from_response(response)
        return new_content
