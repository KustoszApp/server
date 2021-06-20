import factory

from readorganizer_api import types as ro_types
from readorganizer_api.constants import DEFAULT_UPDATE_FREQUENCY
from readorganizer_api.enums import ChannelTypesEnum


class ChannelDataInputFactory(factory.Factory):
    class Meta:
        model = ro_types.ChannelDataInput

    url = factory.Faker("uri")
    channel_type = ChannelTypesEnum.FEED
    title = factory.Faker("text")
    active = True
    update_frequency = DEFAULT_UPDATE_FREQUENCY
    tags = factory.Faker("words", unique=True)
