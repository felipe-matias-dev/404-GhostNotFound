from enum import StrEnum


class ErrorKind(StrEnum):
    SYNTAX = "syntax"
    UNKNOWN_OBJECT = "unknown_object"
    TYPE_MISMATCH = "type_mismatch"
    TIMEOUT = "timeout"


class SqlRejected(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class QueryExecutionError(Exception):
    def __init__(self, kind: ErrorKind, message: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message
