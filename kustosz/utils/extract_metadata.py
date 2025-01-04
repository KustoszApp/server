import logging
import re
import urllib.parse
from datetime import datetime

from django.core.exceptions import ValidationError
from readability.cleaners import html_cleaner
from readability.htmls import build_doc
from readability.htmls import shorten_title
from readability.readability import Unparseable
from requests import Response

from kustosz.types import SingleEntryExtractedMetadata
from kustosz.validators import EntryURLValidator


log = logging.getLogger(__name__)

SUPPORTED_METADATA = (
    "author",
    "link",
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
                # readability default html cleaner removes <link> elements,
                # so we have to copy-paste critical parts here
                doc, encoding = build_doc(content)
                html_cleaner.links = False
                doc = html_cleaner.clean_html(doc)
                doc.make_links_absolute(
                    self._url, resolve_base_href=True, handle_failures="discard"
                )
                self._parsed_content = doc
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
        entry_url_validator = EntryURLValidator()
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
                if meta_key == "link":
                    try:
                        entry_url_validator(value)
                    except ValidationError:
                        continue
                log.debug("%s: setting %s to %s", self._url, meta_key, value)
                metadata[meta_key] = value
                break
        return metadata

    def _get_opengraph_author(self):
        # FIXME: according to spec, author should be "profile array" -
        # and may link to external site that does have this info
        # in practice, many websites just put name here
        og_author = self.__get_meta_value(property="article:author")
        if og_author and "facebook.com" in og_author:
            og_author = og_author.removeprefix("http://facebook.com/")
            og_author = og_author.removeprefix("https://facebook.com/")
            og_author = og_author.removeprefix("http://www.facebook.com/")
            og_author = og_author.removeprefix("http://www.facebook.com/")
        return og_author

    def _get_opengraph_link(self):
        og_url = self.__get_meta_value(property="og:url")
        if og_url:
            og_url_parsed = urllib.parse.urlparse(og_url)
            # rarely, published website will have canonical url reference
            # pointing to localhost - ignore it
            if og_url_parsed.hostname == "localhost":
                return
            # some websites set og:url to main page. They seem to want to route
            # all traffic to whole site instead of specific articles?
            # we have limited ability to detect cases like that, especially if
            # site is stored in directory, but "og:url and url point to the same
            # domain, and og:url does not have path component" seems like a good
            # heuristic
            if (
                og_url_parsed.hostname == self._parsed_url.hostname
                and not og_url_parsed.path.strip("/")
                and self._parsed_url.path.strip("/")
            ):
                return

        # according to spec, URL has to utilize http:// or https:// protocols,
        # but Facebook implementation does handle absolute path
        # (apparently while ignoring <base href="">, if present)
        if og_url and not og_url.startswith(("http://", "https://")):
            og_url_parsed = self._parsed_url._replace(path=og_url)
            og_url = urllib.parse.urlunparse(og_url_parsed)
        return og_url

    def _get_opengraph_title(self):
        return self.__get_meta_value(property="og:title")

    def _get_opengraph_published_time_upstream(self):
        return self.__get_opengraph_time_value(property="article:published_time")

    def _get_opengraph_updated_time_upstream(self):
        return self.__get_opengraph_time_value(property="article:modified_time")

    def _get_html_author(self):
        return self.__get_meta_value(name="author")

    def _get_html_link(self):
        selector = './/link[@rel="canonical"][@href]'
        element = self._parsed_content.find(selector)
        if element is None:
            return
        element_value = element.get("href")
        # rarely, published website will have canonical url reference
        # pointing to localhost - ignore it
        link_url_parsed = urllib.parse.urlparse(element_value)
        if link_url_parsed.hostname == "localhost":
            return

        return element_value

    def _get_html_title(self):
        return shorten_title(self._parsed_content)

    # def _get_html_published_time_upstream(self):
    # def _get_html_updated_time_upstream(self):
    # def _get_headers_author(self):

    def _get_headers_link(self):
        if not self._headers:
            return
        link_header = self._headers.get("Link", "")
        if not link_header:
            return
        canonical_link_re = r'<([^;]*?)>; [^,\n]*rel="[^"]*\bcanonical\b[^"]*"'
        if m := re.search(canonical_link_re, link_header):
            return m.group(1)
        return None

    # def _get_headers_title(self):

    def _get_headers_published_time_upstream(self):
        if not self._headers:
            return
        last_modified_header = self._headers.get("Last-Modified", "")
        if not last_modified_header:
            return
        try:
            last_modified_date = datetime.strptime(
                last_modified_header, "%a, %d %b %Y %H:%M:%S %Z"
            )
        except ValueError:
            log.debug(
                "%s: %s has invalid date %s",
                self._url,
                "Last-Modified",
                last_modified_header,
            )
            return
        return last_modified_date

    def _get_headers_updated_time_upstream(self):
        return self._get_headers_published_time_upstream()

    def _get_url_author(self):
        return self._parsed_url.hostname or self._parsed_url.netloc

    def _get_url_link(self):
        return self._url

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

    def __get_opengraph_time_value(self, **kwargs):
        value: str = self.__get_meta_value(**kwargs)
        if not value:
            return
        if value.lower().endswith("z"):
            value = value.rstrip("zZ")
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            log.debug("%s: %s has invalid date %s", self._url, kwargs, value)
            return

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
