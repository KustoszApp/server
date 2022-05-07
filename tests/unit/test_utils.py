from datetime import datetime

import pytest
from django.utils.http import http_date
from pytest import approx

from ..framework.factories.models import EntryFactory
from ..framework.factories.types import FakeRequestFactory
from ..framework.utils import create_simple_html
from kustosz.utils import estimate_reading_time
from kustosz.utils import normalize_url
from kustosz.utils.extract_metadata import MetadataExtractor
from kustosz.utils.run_script import entry_data_env


@pytest.mark.parametrize(
    "text,expected",
    [
        pytest.param("", 0, id="empty"),
        pytest.param("single", 0.0043, id="single"),
        pytest.param("word " * 300, 1.3043, id="long string"),
        pytest.param("<a>word</a> " * 300, 1.3043, id="long html"),
    ],
)
def test_estimate_reading_time(text, expected):
    assert estimate_reading_time(text) == approx(expected, rel=1e-4, abs=1e-4)


@pytest.mark.parametrize(
    "url,expected",
    [
        pytest.param("http://test/?utm_source=test", "http://test/", id="utm_source"),
        pytest.param("http://test/?b=2&a=1", "http://test/?a=1&b=2", id="params order"),
        pytest.param(
            "http://test/?a=1&utm_source=test&b=2",
            "http://test/?a=1&b=2",
            id="utm_source between other params",
        ),
        pytest.param("http://TEST.COM/", "http://test.com/", id="lowercased"),
    ],
)
def test_normalize_url_sorted_query(url, expected):
    assert normalize_url(url, sort_query=True) == expected


@pytest.mark.parametrize(
    "url,expected",
    [
        pytest.param("http://test/?b=2&a=1", "http://test/?b=2&a=1", id="params order"),
    ],
)
def test_normalize_url_unsorted_query(url, expected):
    assert normalize_url(url, sort_query=False) == expected


def test_metadata_extract_opengraph(faker):
    metadata = {
        "article:author": faker.name(),
        "og:title": faker.sentence(),
        "og:url": faker.uri(),
        "article:published_time": faker.iso8601(),
        "article:modified_time": faker.iso8601(),
    }
    html = create_simple_html(meta=metadata)
    resp = FakeRequestFactory(text=html)

    extracted_metadata = MetadataExtractor.from_response(resp)

    assert extracted_metadata.title == metadata["og:title"]
    assert extracted_metadata.author == metadata["article:author"]
    assert extracted_metadata.link == metadata["og:url"]
    assert extracted_metadata.published_time_upstream == datetime.fromisoformat(
        metadata["article:published_time"]
    )
    assert extracted_metadata.updated_time_upstream == datetime.fromisoformat(
        metadata["article:modified_time"]
    )


def test_metadata_extract_opengraph_dates_with_z(faker):
    correct_date = faker.iso8601()
    date_with_z = f"{correct_date}Z"
    metadata = {
        "article:published_time": date_with_z,
        "article:modified_time": date_with_z,
    }
    html = create_simple_html(meta=metadata)
    resp = FakeRequestFactory(text=html)

    extracted_metadata = MetadataExtractor.from_response(resp)

    assert extracted_metadata.published_time_upstream == datetime.fromisoformat(
        correct_date
    )
    assert extracted_metadata.updated_time_upstream == datetime.fromisoformat(
        correct_date
    )


def test_metadata_extract_opengraph_invalid_dates(faker):
    metadata = {
        "article:published_time": faker.text(),
        "article:modified_time": faker.text(),
    }
    html = create_simple_html(meta=metadata)
    resp = FakeRequestFactory(text=html)

    extracted_metadata = MetadataExtractor.from_response(resp)

    assert not extracted_metadata.published_time_upstream
    assert not extracted_metadata.updated_time_upstream


def test_metadata_extract_html(faker):
    title = faker.sentence()
    metadata = {"author": faker.name()}
    html = create_simple_html(title=title, meta=metadata)
    resp = FakeRequestFactory(text=html)

    extracted_metadata = MetadataExtractor.from_response(resp)

    assert extracted_metadata.title == title
    assert extracted_metadata.author == metadata["author"]
    assert not extracted_metadata.published_time_upstream
    assert not extracted_metadata.updated_time_upstream


def test_metadata_extract_html_link(faker):
    title = faker.sentence()
    url = faker.uri()
    html = (
        "<html><head>"
        f"<title>{title}</title>"
        f"<link rel='canonical' href='{url}'>"
        "</head></html>"
    )
    resp = FakeRequestFactory(text=html)

    extracted_metadata = MetadataExtractor.from_response(resp)

    assert extracted_metadata.title == title
    assert extracted_metadata.link == url


def test_metadata_extract_link_validation(faker):
    url = faker.uri()
    metadata = {
        "og:url": faker.text(),
    }
    html = create_simple_html(meta=metadata)
    resp = FakeRequestFactory(url=url, text=html)

    extracted_metadata = MetadataExtractor.from_response(resp)

    assert extracted_metadata.link == url
    assert extracted_metadata.link != metadata["og:url"]


def test_metadata_extract_opengraph_link_absolute(faker):
    domain = faker.url()
    correct_path = faker.file_path().lstrip("/")
    wrong_path = faker.file_path().lstrip("/")
    og_url = f"{domain}{correct_path}"
    resp_url = f"{domain}{wrong_path}"
    metadata = {"og:url": og_url}
    html = create_simple_html(meta=metadata)
    resp = FakeRequestFactory(url=resp_url, text=html)

    extracted_metadata = MetadataExtractor.from_response(resp)

    assert extracted_metadata.link == og_url
    assert extracted_metadata.link != resp_url


def test_metadata_extract_headers(faker):
    url = faker.uri()
    datetime_obj = faker.date_time()
    headers = {
        "Last-Modified": http_date(datetime_obj.timestamp()),
        "Link": f'<{url}>; rel="canonical"',
    }
    resp = FakeRequestFactory(headers=headers)

    extracted_metadata = MetadataExtractor.from_response(resp)

    assert extracted_metadata.title
    assert extracted_metadata.author
    assert extracted_metadata.link == url
    assert extracted_metadata.published_time_upstream == datetime_obj
    assert extracted_metadata.updated_time_upstream == datetime_obj


@pytest.mark.parametrize(
    "header_text",
    [
        pytest.param('<{0}>; rel="canonical"', id="base-case"),
        pytest.param(
            '<{0}>; rel="canonical"; rel="preconnect"', id="multiple-rels-first"
        ),
        pytest.param(
            '<{0}>; rel="preconnect"; rel="canonical"', id="multiple-rels-last"
        ),
        pytest.param('<{0}>; rel="canonical next"', id="multiple-values-first"),
        pytest.param('<{0}>; rel="prev canonical next"', id="multiple-values-middle"),
        pytest.param('<{0}>; rel="prev canonical"', id="multiple-values-last"),
        pytest.param(
            '<http://example.invalid>; rel="preconnect", <{0}>; rel="canonical"',
            id="multiple-urls-last",
        ),
        pytest.param(
            '<{0}>; rel="canonical", <http://example.invalid>; rel="preconnect"',
            id="multiple-urls-first",
        ),
        pytest.param('<{0}>; rel="stylesheet"', id="no-canonical"),
        pytest.param('<{0}>; title="link title"', id="no-rel"),
        pytest.param("<{0}>", id="no-param"),
    ],
)
def test_metadata_extract_headers_link(faker, request, header_text):
    url = faker.uri()
    headers = {
        "Link": header_text.format(url),
    }
    resp = FakeRequestFactory(headers=headers)

    extracted_metadata = MetadataExtractor.from_response(resp)

    if not request.node.callspec.id.startswith("no"):
        assert extracted_metadata.link == url
    else:
        assert extracted_metadata.link != url


def test_metadata_extract_headers_invalid_dates(faker):
    headers = {
        "Last-Modified": faker.text(),
    }
    resp = FakeRequestFactory(headers=headers)

    extracted_metadata = MetadataExtractor.from_response(resp)

    assert not extracted_metadata.published_time_upstream
    assert not extracted_metadata.updated_time_upstream


def test_metadata_extract_url(faker):
    url = faker.uri()
    resp = FakeRequestFactory(url=url)

    extracted_metadata = MetadataExtractor.from_response(resp)

    assert extracted_metadata.title == url
    assert extracted_metadata.author
    assert not extracted_metadata.published_time_upstream
    assert not extracted_metadata.updated_time_upstream


def test_metadata_extract_mixed(faker):
    url = faker.uri()
    author = faker.name()
    updated_datetime = faker.date_time()
    metadata = {
        "author": author,
        "article:published_time": faker.iso8601(),
    }
    headers = {
        "Last-Modified": http_date(updated_datetime.timestamp()),
    }
    html = create_simple_html(meta=metadata)
    resp = FakeRequestFactory(url=url, headers=headers, text=html)

    extracted_metadata = MetadataExtractor.from_response(resp)

    assert extracted_metadata.title == url
    assert extracted_metadata.author == author
    assert extracted_metadata.published_time_upstream == datetime.fromisoformat(
        metadata["article:published_time"]
    )
    assert extracted_metadata.updated_time_upstream == updated_datetime


def test_entry_data_env(db, faker):
    tags = faker.words(unique=True)
    entry = EntryFactory.create(tags=tags)

    env = entry_data_env(entry)

    for key in ("id", "gid", "link", "updated_time"):
        env_key = f"KUSTOSZ_{key.upper()}"
        assert env[env_key] == str(getattr(entry, key))
    assert env["KUSTOSZ_TAGS"] == ",".join(entry.tags.slugs())
    for key in ("id", "url", "title", "displayed_title", "added_time"):
        env_key = f"KUSTOSZ_CHANNEL_{key.upper()}"
        assert env[env_key] == str(getattr(entry.channel, key))
    other_env = {k: v for k, v in env.items() if not k.startswith("KUSTOSZ_")}
    assert other_env
