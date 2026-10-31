from enum import StrEnum


class ErrorKind(StrEnum):
    SYNTAX = "syntax"
    UNKNOWN_OBJECT = "unknown_object"
    TYPE_MISMATCH = "type_mismatch"
    TIMEOUT = "timeout"
    REJECTED = "rejected"


class SqlRejected(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class QueryExecutionError(Exception):
    def __init__(self, kind: ErrorKind, message: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message


class ModelCallFailed(Exception):
    def __init__(self, input_tokens: int, output_tokens: int) -> None:
        super().__init__("a chamada ao modelo falhou")
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
