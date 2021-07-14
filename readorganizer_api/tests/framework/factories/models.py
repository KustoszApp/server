import factory
from django.utils.timezone import now
from factory.django import DjangoModelFactory

from readorganizer_api import models as ro_models
from readorganizer_api.constants import DEFAULT_UPDATE_FREQUENCY
from readorganizer_api.enums import ChannelTypesEnum


class ChannelFactory(DjangoModelFactory):
    class Meta:
        model = ro_models.Channel

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

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        self.tags.add(*extracted)


class EntryFactory(DjangoModelFactory):
    class Meta:
        model = ro_models.Entry

    channel = factory.SubFactory(ChannelFactory)
    gid = factory.Faker("uri")
    archived = False
    link = factory.Faker("uri")
    title = factory.Faker("text")
    author = factory.Faker("name")
    updated_time = factory.LazyFunction(now)
    published_time_upstream = factory.LazyFunction(now)
    updated_time_upstream = factory.LazyFunction(now)

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        self.tags.add(*extracted)
