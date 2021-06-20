from datetime import datetime

import factory
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
    last_check_time = factory.LazyFunction(datetime.now)
    last_successful_check_time = factory.LazyFunction(datetime.now)
    added_time = factory.LazyFunction(datetime.now)
    active = True
    update_frequency = DEFAULT_UPDATE_FREQUENCY
