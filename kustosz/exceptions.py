from django.core.exceptions import ValidationError


class ChildrenTasksInProgress(Exception):
    pass


class InvalidDataException(ValidationError):
    pass


class NoNewChannelsAddedException(Exception):
    pass


class PermanentFetcherError(Exception):
    pass


class SerialTaskAlreadyInProgress(Exception):
    pass


class TransientFetcherError(Exception):
    pass
