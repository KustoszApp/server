import logging
import urllib.parse
from datetime import datetime

from readability import Document
from readability.htmls import shorten_title
from readability.readability import Unparseable
from requests import Response

from readorganizer_api.types import SingleEntryExtractedMetadata


log = logging.getLogger(__name__)

SUPPORTED_METADATA = (
    "author",
    "title",
    "published_time_upstream",
    "updated_time_upstream",
)
SUPPORTED_SOURCES = ("opengraph", "html", "headers", "url")


class MetadataExtractor:
    def __init__(self, metadata=None, sources=None):
        self._metadata_keys = metadata or SUPPORTED_METADATA
        self._sources = sources or SUPPORTED_SOURCES
        self._applicable_sources = ("url",)
        self._url = None
        self._parsed_url = None
        self._headers = None
        self._parsed_content = None

    def _from_response(self, response: Response) -> SingleEntryExtractedMetadata:
        self._url = response.url
        self._parsed_url = urllib.parse.urlparse(self._url)
        if response.headers:
            self._headers = response.headers
            self._applicable_sources = ("headers", "url")
        content = response.text
        if content.strip():
            try:
                doc = Document(content)
                doc.title()  # this forces Document to create lxml tree under html
                self._parsed_content = doc.html
                self._applicable_sources = SUPPORTED_SOURCES
            except Unparseable:
                pass

        metadata = self._get_all_metadata()
        return SingleEntryExtractedMetadata(**metadata)

    def _from_url(self, url: str) -> SingleEntryExtractedMetadata:
        self._url = url
        self._parsed_url = urllib.parse.urlparse(self._url)
        metadata = self._get_all_metadata()
        return SingleEntryExtractedMetadata(**metadata)

    def _get_all_metadata(self):
        metadata = {}
        sources = tuple(
            source for source in self._applicable_sources if source in self._sources
        )
        for meta_key in self._metadata_keys:
            for source_name in sources:
                function_name = f"_get_{source_name}_{meta_key}"
                function = getattr(self, function_name, None)
                if not function:
                    continue
                value = function()
                log.debug("%s: %s returned %s", self._url, function_name, value)
                if not value:
                    continue
                metadata[meta_key] = value
                break
        return metadata

    def _get_opengraph_author(self):
        # FIXME: according to spec, author should be "profile array" -
        # and may link to external site that does have this info
        # in practice, many websites just put name here
        return self.__get_meta_value(property="article:author")

    def _get_opengraph_title(self):
        return self.__get_meta_value(property="og:title")

    def _get_opengraph_published_time_upstream(self):
        value = self.__get_meta_value(property="article:published_time")
        if not value:
            return
        return datetime.fromisoformat(value)

    def _get_opengraph_updated_time_upstream(self):
        value = self.__get_meta_value(property="article:modified_time")
        if not value:
            return
        return datetime.fromisoformat(value)

    def _get_html_author(self):
        return self.__get_meta_value(name="author")

    def _get_html_title(self):
        return shorten_title(self._parsed_content)

    # def _get_html_published_time_upstream(self):
    # def _get_html_updated_time_upstream(self):
    # def _get_headers_author(self):
    # def _get_headers_title(self):

    def _get_headers_published_time_upstream(self):
        if not self._headers:
            return
        last_modified_header = self._headers.get("Last-Modified", "")
        if not last_modified_header:
            return
        last_modified_date = datetime.strptime(
            last_modified_header, "%a, %d %b %Y %H:%M:%S %Z"
        )
        return last_modified_date

    def _get_headers_updated_time_upstream(self):
        return self._get_headers_published_time_upstream()

    def _get_url_author(self):
        return self._parsed_url.hostname or self._parsed_url.netloc

    def _get_url_title(self):
        return self._url

    # def _get_url_published_time_upstream(self):
    # def _get_url_updated_time_upstream(self):

    def __get_meta_value(self, **kwargs):
        attrs = " and ".join([f'@{key}="{value}"' for key, value in kwargs.items()])
        selector = f".//meta[{attrs}]"
        element = self._parsed_content.find(selector)
        if element is None:
            return
        element_value = element.get("content")
        return element_value

    @classmethod
    def from_response(
        cls, response: Response, **kwargs
    ) -> SingleEntryExtractedMetadata:
        extractor = cls(**kwargs)
        extracted_metadata = extractor._from_response(response)
        return extracted_metadata

    @classmethod
    def from_url(cls, url: str, **kwargs) -> SingleEntryExtractedMetadata:
        extractor = cls(**kwargs)
        extracted_metadata = extractor._from_url(url)
        return extracted_metadata
