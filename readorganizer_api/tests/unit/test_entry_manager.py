from datetime import timedelta

from django.utils.timezone import now as django_now
from freezegun import freeze_time

from ..framework.factories.models import EntryFactory
from readorganizer_api.models import Entry


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
