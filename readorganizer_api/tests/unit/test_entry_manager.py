from datetime import timedelta

from django.utils.timezone import now as django_now
from freezegun import freeze_time

import readorganizer_api
from ..framework.factories.models import ChannelFactory
from ..framework.factories.models import EntryFactory
from ..framework.factories.models import EntryFilterFactory
from readorganizer_api.enums import EntryFilterActionsEnum
from readorganizer_api.managers import DuplicateFinder
from readorganizer_api.models import Entry
from readorganizer_api.models import EntryFilter


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


def test_deduplication_ignores_archived(db):
    one = EntryFactory.create()
    another = EntryFactory.create()
    duplicate = EntryFactory.create(gid=one.gid, archived=True)
    duplicate_updated_time = duplicate.updated_time
    m = Entry.objects

    m.deduplicate_entries(1)

    for model in (one, another, duplicate):
        model.refresh_from_db()
    assert duplicate.updated_time == duplicate_updated_time


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
    mocker.patch(
        "readorganizer_api.managers.EntryManager._EntryManager__get_filtered_entries"
    )
    one = EntryFactory.create()
    another = EntryFactory.create()
    m = Entry.objects

    m._run_filters_on_entries([one.pk, another.pk], EntryFilter.objects.all())

    for model in (one, another):
        model.refresh_from_db()

    assert one.archived is False
    assert another.archived is False
    assert (
        not readorganizer_api.managers.EntryManager._EntryManager__get_filtered_entries.called  # noqa
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