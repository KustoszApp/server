from django.core.exceptions import ValidationError


class InvalidDataException(ValidationError):
    pass


class SerialTaskAlreadyInProgress(Exception):
    pass


class NoNewChannelsAddedException(Exception):
    pass
