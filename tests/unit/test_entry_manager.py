from datetime import timedelta

from django.utils.timezone import now as django_now
from freezegun import freeze_time

import kustosz
from ..framework.factories.models import ChannelFactory
from ..framework.factories.models import EntryFactory
from ..framework.factories.models import EntryFilterFactory
from ..framework.factories.types import ReadabilityContentListFactory
from ..framework.factories.types import SingleEntryExtractedMetadataFactory
from kustosz.enums import EntryFilterActionsEnum
from kustosz.managers import DuplicateFinder
from kustosz.models import Entry
from kustosz.models import EntryFilter


def test_deduplication_same_gid(db):
    one = EntryFactory.create()
    another = EntryFactory.create()
    duplicate = EntryFactory.create(gid=one.gid)
    m = Entry.objects

    m.deduplicate_entries(1)

    for model in (one, another, duplicate):
        model.refresh_from_db()

    assert one.archived is False
    assert another.archived is False
    assert duplicate.archived is True


def test_deduplication_same_links(db):
    one = EntryFactory.create()
    another = EntryFactory.create()
    duplicate = EntryFactory.create(link=one.link)
    m = Entry.objects

    m.deduplicate_entries(1)

    for model in (one, another, duplicate):
        model.refresh_from_db()

    assert one.archived is False
    assert another.archived is False
    assert duplicate.archived is True


def test_deduplication_same_author_title(db):
    one = EntryFactory.create()
    another = EntryFactory.create()
    duplicate = EntryFactory.create(author=one.author, title=one.title)
    m = Entry.objects

    m.deduplicate_entries(1)

    for model in (one, another, duplicate):
        model.refresh_from_db()

    assert one.archived is False
    assert another.archived is False
    assert duplicate.archived is True


def test_deduplication_works_only_across_channels(db):
    one = EntryFactory.create()
    another = EntryFactory.create()
    duplicate = EntryFactory.create(channel=one.channel, link=one.link)
    m = Entry.objects

    m.deduplicate_entries(1)

    for model in (one, another, duplicate):
        model.refresh_from_db()

    assert one.archived is False
    assert another.archived is False
    assert duplicate.archived is False


def test_deduplication_first_match_marks_as_duplicated(db, mocker):
    get_gid_spy = mocker.spy(DuplicateFinder, "get_gid")
    get_normalized_link_spy = mocker.spy(DuplicateFinder, "get_normalized_link")
    one = EntryFactory.create()
    another = EntryFactory.create()
    duplicate = EntryFactory.create(gid=one.gid, link=one.link)
    m = Entry.objects

    m.deduplicate_entries(1)

    for model in (one, another, duplicate):
        model.refresh_from_db()

    assert duplicate in get_gid_spy.call_args.args
    assert duplicate not in get_normalized_link_spy.call_args.args
    assert get_gid_spy.call_count == 3
    assert get_normalized_link_spy.call_count == 2


def test_deduplication_time_limit(db):
    with freeze_time(django_now() - timedelta(days=5)):
        one = EntryFactory.create()
    another = EntryFactory.create()
    would_be_duplicate = EntryFactory.create(gid=one.gid)
    m = Entry.objects

    m.deduplicate_entries(1)

    for model in (one, another, would_be_duplicate):
        model.refresh_from_db()
        assert model.archived is False


def test_deduplication_ignores_archived_before_deduplication(db):
    one = EntryFactory.create()
    another = EntryFactory.create()
    duplicate = EntryFactory.create(gid=one.gid, archived=True)
    duplicate_updated_time = duplicate.updated_time
    m = Entry.objects

    m.deduplicate_entries(1)

    for model in (one, another, duplicate):
        model.refresh_from_db()
    assert duplicate.updated_time == duplicate_updated_time


def test_deduplication_uses_archived_entries(db):
    one = EntryFactory.create(archived=True)
    duplicate = EntryFactory.create(gid=one.gid)
    m = Entry.objects

    m.deduplicate_entries(1)

    for model in (one, duplicate):
        model.refresh_from_db()
    assert one.archived is True
    assert duplicate.archived is True


def test_deduplication_ignores_already_deduplicated(db):
    one = EntryFactory.create()
    another = EntryFactory.create()
    duplicate = EntryFactory.create(gid=one.gid)
    m = Entry.objects

    m.deduplicate_entries(1)
    duplicate.refresh_from_db()
    duplicate_updated_time = duplicate.updated_time
    m.deduplicate_entries(1)

    for model in (one, another, duplicate):
        model.refresh_from_db()
    assert duplicate.archived is True
    assert duplicate.updated_time == duplicate_updated_time


def test_deduplication_ignores_deduplication_disabled(db):
    duplicate_channel = ChannelFactory.create(deduplication_enabled=False)
    one = EntryFactory.create()
    another = EntryFactory.create()
    duplicate = EntryFactory.create(channel=duplicate_channel, gid=one.gid)

    m = Entry.objects

    m.deduplicate_entries(1)

    for model in (one, another, duplicate):
        model.refresh_from_db()

    assert one.archived is False
    assert another.archived is False
    assert duplicate.archived is False


def test_filter_mark_as_read(db):
    one = EntryFactory.create()
    another = EntryFactory.create()
    EntryFilterFactory.create(condition=f"link={one.link}")
    m = Entry.objects

    m._run_filters_on_entries([one.pk, another.pk], EntryFilter.objects.all())

    for model in (one, another):
        model.refresh_from_db()

    assert one.archived is True
    assert another.archived is False


def test_filter_mark_assign_tag(db):
    one = EntryFactory.create()
    another = EntryFactory.create()
    EntryFilterFactory.create(
        condition=f"link={one.link}",
        action_name=EntryFilterActionsEnum.ASSIGN_TAG,
        action_argument="Whatever",
    )
    m = Entry.objects

    m._run_filters_on_entries([one.pk, another.pk], EntryFilter.objects.all())

    for model in (one, another):
        model.refresh_from_db()

    assert "Whatever" in one.tags.names()
    assert "Whatever" not in another.tags.names()


def test_filter_mark_assign_multiple_tags(db):
    one = EntryFactory.create()
    another = EntryFactory.create()
    EntryFilterFactory.create(
        condition=f"link={one.link}",
        action_name=EntryFilterActionsEnum.ASSIGN_TAG,
        action_argument="Foo, Bar",
    )
    m = Entry.objects

    m._run_filters_on_entries([one.pk, another.pk], EntryFilter.objects.all())

    for model in (one, another):
        model.refresh_from_db()

    assert "Foo" in one.tags.names()
    assert "Bar" in one.tags.names()
    assert "Foo, Bar" not in one.tags.names()
    assert "Foo" not in another.tags.names()


def test_filter_no_matches(db):
    one = EntryFactory.create()
    another = EntryFactory.create()
    EntryFilterFactory.create(condition="archived=True")
    m = Entry.objects

    m._run_filters_on_entries([one.pk, another.pk], EntryFilter.objects.all())

    for model in (one, another):
        model.refresh_from_db()

    assert one.archived is False
    assert another.archived is False


def test_filter_none_defined(db, mocker):
    mocker.patch("kustosz.managers.EntryManager._EntryManager__get_filtered_entries")
    one = EntryFactory.create()
    another = EntryFactory.create()
    m = Entry.objects

    m._run_filters_on_entries([one.pk, another.pk], EntryFilter.objects.all())

    for model in (one, another):
        model.refresh_from_db()

    assert one.archived is False
    assert another.archived is False
    assert (
        not kustosz.managers.EntryManager._EntryManager__get_filtered_entries.called  # noqa
    )


def test_filter_none_enabled(db):
    one = EntryFactory.create()
    another = EntryFactory.create()
    EntryFilterFactory.create(enabled=False, condition=f"link={one.link}")
    m = Entry.objects

    m._run_filters_on_entries([one.pk, another.pk], EntryFilter.objects.all())

    for model in (one, another):
        model.refresh_from_db()

    assert one.archived is False
    assert another.archived is False


def test_manual_entry_update_metadata(db, mocker):
    extracted_data = SingleEntryExtractedMetadataFactory()
    mocker.patch("kustosz.managers.SingleURLFetcher.fetch")
    mocker.patch(
        "kustosz.managers.MetadataExtractor.from_response",
        return_value=extracted_data,
    )
    entry = EntryFactory.create(
        link="",
        title="",
        author="",
        published_time_upstream=None,
        updated_time_upstream=None,
    )
    m = Entry.objects

    m._ensure_manual_entry_metadata(entry.pk)

    entry.refresh_from_db()
    assert entry.author == extracted_data.author
    assert entry.link == extracted_data.link
    assert entry.title == extracted_data.title
    assert entry.published_time_upstream == extracted_data.published_time_upstream
    assert entry.updated_time_upstream == extracted_data.updated_time_upstream


def test_manual_entry_skip_update_metadata_when_filled(db, mocker):
    mocker.patch("kustosz.managers.SingleURLFetcher.fetch")
    mocker.patch("kustosz.managers.MetadataExtractor.from_response")
    entry = EntryFactory.create()
    m = Entry.objects

    m._ensure_manual_entry_metadata(entry.pk)

    assert not kustosz.managers.SingleURLFetcher.fetch.called
    assert not kustosz.managers.MetadataExtractor.from_response.called


def test_manual_entry_update_metadata_only_author(db, mocker):
    extracted_data = SingleEntryExtractedMetadataFactory()
    mocker.patch("kustosz.managers.SingleURLFetcher.fetch")
    mocker.patch(
        "kustosz.managers.MetadataExtractor.from_response",
        return_value=extracted_data,
    )
    entry = EntryFactory.create(
        author="", published_time_upstream=None, updated_time_upstream=None
    )
    m = Entry.objects

    m._ensure_manual_entry_metadata(entry.pk)

    old_link = entry.link
    old_title = entry.title
    entry.refresh_from_db()
    assert entry.author == extracted_data.author
    assert entry.link != old_link
    assert entry.link == extracted_data.link
    assert entry.title == old_title
    assert entry.title != extracted_data.title
    assert entry.published_time_upstream == extracted_data.published_time_upstream
    assert entry.updated_time_upstream == extracted_data.updated_time_upstream


def test_manual_entry_update_metadata_only_link(db, mocker):
    extracted_data = SingleEntryExtractedMetadataFactory()
    mocker.patch("kustosz.managers.SingleURLFetcher.fetch")
    mocker.patch(
        "kustosz.managers.MetadataExtractor.from_response",
        return_value=extracted_data,
    )
    # We *always* have link, so we need empty title to trigger request,
    # which might tell us that URL updated
    entry = EntryFactory.create(
        link="", title="", published_time_upstream=None, updated_time_upstream=None
    )
    m = Entry.objects

    m._ensure_manual_entry_metadata(entry.pk)

    old_author = entry.author
    old_title = entry.title
    entry.refresh_from_db()
    assert entry.link == extracted_data.link
    assert entry.author == old_author
    assert entry.author != extracted_data.author
    assert entry.title != old_title
    assert entry.title == extracted_data.title
    assert entry.published_time_upstream == extracted_data.published_time_upstream
    assert entry.updated_time_upstream == extracted_data.updated_time_upstream


def test_manual_entry_update_metadata_link_redirect(db, faker, mocker):
    old_url = faker.uri()
    new_url = faker.uri()
    extracted_data = SingleEntryExtractedMetadataFactory(link=new_url)
    mocker.patch("kustosz.managers.SingleURLFetcher.fetch")
    mocker.patch(
        "kustosz.managers.MetadataExtractor.from_response",
        return_value=extracted_data,
    )
    entry = EntryFactory.create(gid=old_url, link=old_url, title="")
    m = Entry.objects

    m._ensure_manual_entry_metadata(entry.pk)

    entry.refresh_from_db()
    assert entry.link == new_url
    assert entry.gid == old_url


def test_manual_entry_update_metadata_only_title(db, mocker):
    extracted_data = SingleEntryExtractedMetadataFactory()
    mocker.patch("kustosz.managers.SingleURLFetcher.fetch")
    mocker.patch(
        "kustosz.managers.MetadataExtractor.from_response",
        return_value=extracted_data,
    )
    entry = EntryFactory.create(
        title="", published_time_upstream=None, updated_time_upstream=None
    )
    m = Entry.objects

    m._ensure_manual_entry_metadata(entry.pk)

    old_author = entry.author
    old_link = entry.link
    entry.refresh_from_db()
    assert entry.author == old_author
    assert entry.author != extracted_data.author
    assert entry.link != old_link
    assert entry.link == extracted_data.link
    assert entry.title == extracted_data.title
    assert entry.published_time_upstream == extracted_data.published_time_upstream
    assert entry.updated_time_upstream == extracted_data.updated_time_upstream


def test_manual_entry_update_metadata_no_upstream_times(db, mocker):
    extracted_data = SingleEntryExtractedMetadataFactory(
        published_time_upstream=None, updated_time_upstream=None
    )
    mocker.patch("kustosz.managers.SingleURLFetcher.fetch")
    mocker.patch(
        "kustosz.managers.MetadataExtractor.from_response",
        return_value=extracted_data,
    )
    entry = EntryFactory.create(
        title="", author="", published_time_upstream=None, updated_time_upstream=None
    )
    m = Entry.objects

    m._ensure_manual_entry_metadata(entry.pk)

    entry.refresh_from_db()
    assert entry.title == extracted_data.title
    assert entry.author == extracted_data.author
    assert not entry.published_time_upstream
    assert not entry.updated_time_upstream


def test_add_readability(db, mocker):
    extracted_data = ReadabilityContentListFactory()
    mocker.patch("kustosz.managers.SingleURLFetcher.fetch")
    mocker.patch(
        "kustosz.managers.ReadabilityContentExtractor.from_response",
        return_value=extracted_data,
    )
    entry = EntryFactory.create()
    m = Entry.objects

    m._add_readability_contents(entry.pk)

    entry.refresh_from_db()
    assert entry.readability_fetch_time is not None
    assert entry.readability_fetch_time == entry.updated_time
    entry_content = entry.content_set.first()
    assert entry_content.source == extracted_data.content[0].source
    assert entry_content.content == extracted_data.content[0].content
    assert entry_content.mimetype == extracted_data.content[0].mimetype
