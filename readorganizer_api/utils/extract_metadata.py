import urllib.parse
from datetime import datetime

from requests import Response

from readorganizer_api.types import SingleEntryExtractedMetadata


class MetadataExtractor:
    def _from_response(self, response: Response) -> SingleEntryExtractedMetadata:
        # FIXME: this is really only fallback that should be used only for data
        # we did not manage to extract from html content (if one is available)
        metadata = {}
        parsed = urllib.parse.urlparse(response.url)
        metadata["title"] = response.url
        metadata["author"] = parsed.hostname or parsed.netloc

        last_modified_header = response.headers.get("Last-Modified", "")
        if last_modified_header:
            last_modified_date = datetime.strptime(
                last_modified_header, "%a, %d %b %Y %H:%M:%S %Z"
            )
            metadata["published_time_upstream"] = last_modified_date
            metadata["updated_time_upstream"] = last_modified_date
        return SingleEntryExtractedMetadata(**metadata)

    @classmethod
    def from_response(cls, response: Response) -> SingleEntryExtractedMetadata:
        extractor = cls()
        new_metadata = extractor._from_response(response)
        return new_metadata
