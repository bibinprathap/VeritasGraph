class StructuredError(Exception):
    """Base class; the message is safe to return to callers."""


class NotFound(StructuredError):
    pass


class Conflict(StructuredError):
    pass


class Invalid(StructuredError):
    pass


class UnsafeConnection(Invalid):
    pass


class SqlRejected(Invalid):
    pass


class IndexMismatch(StructuredError):
    pass
