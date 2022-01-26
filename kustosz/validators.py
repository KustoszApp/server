from django.core.validators import URLValidator
from django.utils.deconstruct import deconstructible


EntryURLValidator = URLValidator


@deconstructible
class ChannelURLValidator:
    django_url_validator_schemes = ("http", "https")
    custom_validator_schemes = ("file",)

    def __call__(self, value):
        if value.startswith(self.custom_validator_schemes):
            return

        url_validator = URLValidator(schemes=self.django_url_validator_schemes)
        url_validator(value)

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and self.django_url_validator_schemes == other.django_url_validator_schemes
            and self.custom_validator_schemes == other.custom_validator_schemes
        )
