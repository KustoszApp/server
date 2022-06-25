import pytest
from dominate import tags as t

from ..framework.factories.types import FakeRequestFactory
from ..framework.utils import create_simple_html
from kustosz.utils.autodetect_content import AutodetectContent
from kustosz.utils.autodetect_content import content_is_feed
from kustosz.utils.autodetect_content import FeedLinksFinder


@pytest.mark.parametrize(
    "text,expected",
    [
        pytest.param(
            (
                '<?xml version="1.0" encoding="utf-8"?>'
                '<feed xmlns="http://www.w3.org/2005/Atom"><title>test</title></feed>'
            ),
            True,
            id="atom_feed",
        ),
        pytest.param(
            '<?xml version="1.0" encoding="utf-8"?><rss version="2.0"><channel/></rss>',
            True,
            id="rss_feed",
        ),
        pytest.param(
            create_simple_html(title="test"),
            False,
            id="html_page",
        ),
    ],
)
def test_estimate_reading_time(text, expected):
    assert content_is_feed(text) == expected


def test_feed_links_from_simple_url(faker):
    hostname = f"http://{faker.domain_name()}"
    flf = FeedLinksFinder(hostname, None)
    found_links = list(flf._from_url(hostname))

    for suffix in ("feed", "feed.xml", "index.xml", "rss.xml", "atom.xml"):
        assert f"{hostname}/{suffix}" in found_links


def test_feed_links_from_url_with_subdirs(faker):
    hostname = f"http://{faker.domain_name()}"
    path = "/one/two/three"
    url = f"{hostname}{path}"
    flf = FeedLinksFinder(url, None)
    found_links = list(flf._from_url(url))

    assert f"{hostname}/one/two/three/feed" in found_links
    assert f"{hostname}/one/two/feed.xml" in found_links
    assert f"{hostname}/one/rss.xml" in found_links
    assert f"{hostname}/atom.xml" in found_links


@pytest.mark.parametrize(
    "content,expected",
    [
        pytest.param(
            (
                "<html><head>"
                '<link rel="alternate" type="application/rss+xml"'
                ' href="http://test.com"></head></html>'
            ),
            "http://test.com/",
            id="link_rel_alternate",
        ),
        pytest.param(
            (
                "<html><head>"
                '<link name="alternate" type="application/rss+xml"'
                ' href="http://test.com"></head></html>'
            ),
            "http://test.com/",
            id="link_name_alternate",
        ),
        pytest.param(
            (
                "<html><head>"
                '<link rel="alternative" type="application/rss+xml"'
                ' href="http://test.com"></head></html>'
            ),
            "http://test.com/",
            id="link_rel_alternative",
        ),
        pytest.param(
            (
                "<html><head>"
                '<link rel="alternative" type="invalid" href="http://test-wrong.com">'
                '<link rel="alternative" type="application/rss+xml"'
                ' href="http://test-correct.com"></head></html>'
            ),
            "http://test-correct.com/",
            id="link_invalid_type",
        ),
        pytest.param(
            t.a(href="http://test.com/", title="my feed content"),
            "http://test.com/",
            id="a_only_title",
        ),
        pytest.param(
            t.a(href="http://test.com/atom.xml"),
            "http://test.com/atom.xml",
            id="a_only_href",
        ),
        pytest.param(
            t.a("RSS", href="http://test.com/somelink/"),
            "http://test.com/somelink/",
            id="a_only_content",
        ),
        pytest.param(
            t.a("RSS", href="http://test.com/some/../link/"),
            "http://test.com/link/",
            id="normalize_path",
        ),
    ],
)
def test_feed_links_from_response(content, expected):
    if not isinstance(content, str):
        content = create_simple_html(body=content)
    response = FakeRequestFactory(
        text=content,
        encoding="utf-8",
    )
    flf = FeedLinksFinder(response.url, response)
    found_links = list(flf._from_response())
    assert expected in found_links


def test_feed_links_from_response_double_slash(faker):
    url = faker.uri()
    content = create_simple_html(body=t.a(href="//example.com/feed/"))
    response = FakeRequestFactory(
        text=content,
        encoding="utf-8",
        url=url,
    )
    flf = FeedLinksFinder(response.url, response)
    found_links = list(flf._from_response())
    scheme, _ = url.split("://")
    assert f"{scheme}://example.com/feed/" in found_links


@pytest.mark.parametrize(
    "href",
    [
        pytest.param("/some/url", id="link_absolute"),
        pytest.param("another/url", id="link_relative"),
        pytest.param("./another/url", id="link_relative_with_dot"),
    ],
)
def test_feed_links_from_response_format(href, faker, request):
    hostname = f"https://{faker.domain_name()}"
    content = create_simple_html(body=t.a("atom", href=href))
    response = FakeRequestFactory(
        text=content,
        encoding="utf-8",
        url=hostname,
    )
    flf = FeedLinksFinder(response.url, response)
    found_links = list(flf._from_response())
    if request.node.callspec.id == "link_relative":
        href = f"/{href}"
    if request.node.callspec.id == "link_relative_with_dot":
        href = href[1:]
    assert f"{hostname}{href}" in found_links


def test_detect_entry_content(mocker):
    headers = {
        "Content-Type": "text/html",
    }
    response = FakeRequestFactory(headers=headers)
    mocker.patch(
        "kustosz.utils.autodetect_content.SingleURLFetcher.fetch", return_value=response
    )
    adc = AutodetectContent(url=response.url)
    entry_content = adc._run_entry_content()
    for key in (
        "gid",
        "link",
        "title",
        "author",
        "published_time_upstream",
        "updated_time_upstream",
        "published_time",
    ):
        assert key in entry_content


def test_detect_entry_content_no_content_type(mocker):
    response = FakeRequestFactory()
    mocker.patch(
        "kustosz.utils.autodetect_content.SingleURLFetcher.fetch", return_value=response
    )
    adc = AutodetectContent(url=response.url)
    entry_content = adc._run_entry_content()
    for key in ("gid", "link"):
        assert entry_content.get(key) == response.url


def test_detect_entry_content_content_type_pdf(mocker):
    headers = {
        "Content-Type": "application/pdf",
    }
    response = FakeRequestFactory(headers=headers)
    mocker.patch(
        "kustosz.utils.autodetect_content.SingleURLFetcher.fetch", return_value=response
    )
    adc = AutodetectContent(url=response.url)
    entry_content = adc._run_entry_content()
    for key in ("gid", "link"):
        assert entry_content.get(key) == response.url


def test_detect_entry_content_content_is_feed(mocker):
    headers = {
        "Content-Type": "text/html",
    }
    response = FakeRequestFactory(
        headers=headers,
        text=(
            '<?xml version="1.0" encoding="utf-8"?>'
            '<feed xmlns="http://www.w3.org/2005/Atom">'
            "<title>test</title></feed>"
        ),
    )
    mocker.patch(
        "kustosz.utils.autodetect_content.SingleURLFetcher.fetch", return_value=response
    )
    adc = AutodetectContent(url=response.url)
    entry_content = adc._run_entry_content()
    assert not entry_content
