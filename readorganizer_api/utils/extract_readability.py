from typing import Optional

from django.conf import settings
from readability import Document
from readability.readability import Unparseable
from requests import Response

from readorganizer_api.enums import EntryContentSourceTypesEnum
from readorganizer_api.types import FetchedFeedEntryContent
from readorganizer_api.types import ReadabilityContentList


class ReadabilityContentExtractor:
    def _get_python_readability(
        self, response: Response
    ) -> Optional[FetchedFeedEntryContent]:
        doc = Document(response.text)
        try:
            extracted_content = doc.summary(html_partial=False)
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
        msg = "extracting readability using node library is not supported yet"
        raise NotImplementedError(msg)

    def _from_response(self, response: Response) -> ReadabilityContentList:
        obtained_content = []
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type or not response.text.strip():
            return ReadabilityContentList(content=tuple(obtained_content))

        if settings.READORGANIZER_READABILITY_PYTHON_ENABLED:
            content = self._get_python_readability(response)
            if content:
                obtained_content.append(content)

        if settings.READORGANIZER_READABILITY_NODE_ENABLED:
            obtained_content.append(self._get_node_readability(response))

        return ReadabilityContentList(content=tuple(obtained_content))

    @classmethod
    def from_response(cls, response: Response) -> ReadabilityContentList:
        extractor = cls()
        new_content = extractor._from_response(response)
        return new_content
