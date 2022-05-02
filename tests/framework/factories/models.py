import factory.fuzzy
from django.utils.timezone import now
from factory.django import DjangoModelFactory

from kustosz import models as kustosz_models
from kustosz.constants import DEFAULT_UPDATE_FREQUENCY
from kustosz.enums import ChannelTypesEnum
from kustosz.enums import EntryContentSourceTypesEnum
from kustosz.enums import EntryFilterActionsEnum


class ChannelFactory(DjangoModelFactory):
    class Meta:
        model = kustosz_models.Channel

    url = factory.Faker("uri")
    channel_type = ChannelTypesEnum.FEED
    title = factory.Faker("text")
    title_upstream = factory.Faker("text")
    link = factory.Faker("uri")
    last_check_time = factory.LazyFunction(now)
    last_successful_check_time = factory.LazyFunction(now)
    added_time = factory.LazyFunction(now)
    active = True
    update_frequency = DEFAULT_UPDATE_FREQUENCY
    deduplication_enabled = True

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        self.tags.add(*extracted)

    @factory.post_generation
    def entries(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            assert isinstance(extracted, int)
            EntryFactory.create_batch(size=extracted, channel=self, **kwargs)


class EntryContentFactory(DjangoModelFactory):
    class Meta:
        model = kustosz_models.EntryContent

    source = factory.fuzzy.FuzzyChoice(EntryContentSourceTypesEnum.values)
    content = factory.Faker("text")
    mimetype = factory.Faker("mime_type", category="text")
    language = factory.Faker("locale")
    estimated_reading_time = factory.Faker("pyfloat", positive=True)
    updated_time = factory.LazyFunction(now)


class EntryFactory(DjangoModelFactory):
    class Meta:
        model = kustosz_models.Entry

    channel = factory.SubFactory(ChannelFactory)
    gid = factory.Faker("uri")
    archived = False
    link = factory.Faker("uri")
    title = factory.Faker("text")
    author = factory.Faker("name")
    note = factory.Faker("text")
    reader_position = 0
    selected_preferred_content = None
    updated_time = factory.LazyFunction(now)
    published_time_upstream = factory.LazyFunction(now)
    updated_time_upstream = factory.LazyFunction(now)
    readability_fetch_time = factory.LazyFunction(now)

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        self.tags.add(*extracted)

    @factory.post_generation
    def content_set(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            assert isinstance(extracted, int)
            EntryContentFactory.create_batch(size=extracted, entry=self, **kwargs)


class EntryFilterFactory(DjangoModelFactory):
    class Meta:
        model = kustosz_models.EntryFilter

    enabled = True
    name = factory.Faker("text")
    condition = "archived=False"
    action_name = EntryFilterActionsEnum.MARK_AS_READ
    action_argument = ""
