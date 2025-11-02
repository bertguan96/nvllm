from dataclasses import dataclass
from typing import Any
from enum import Enum
from dataclasses import field


class ResponseMessage(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not found"
    METHOD_NOT_ALLOWED = "method not allowed"
    NOT_ACCEPTABLE = "not acceptable"
    REQUEST_TIMEOUT = "request timeout"
    CONFLICT = "conflict"
    GONE = "gone"
    LENGTH_REQUIRED = "length required"
    
class ResponseCode(int, Enum):
    SUCCESS = 200
    ERROR = 500
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    NOT_ACCEPTABLE = 406
    REQUEST_TIMEOUT = 408
    CONFLICT = 409
    GONE = 410
    LENGTH_REQUIRED = 411

class ResponseStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not found"
    METHOD_NOT_ALLOWED = "method not allowed"
    NOT_ACCEPTABLE = "not acceptable"
    REQUEST_TIMEOUT = "request timeout"
    CONFLICT = "conflict"
    GONE = "gone"
    LENGTH_REQUIRED = "length required"


@dataclass
class Response:
    """
    Response model, used to store response information
    Args:
        message: Message (required)
        status: Status (required)
        code: Code (required)
        data: Data (required)
    """
    message: ResponseMessage
    status: ResponseStatus
    code: ResponseCode
    trace_id: str
    data: Any = None
    error: str = field(default_factory=lambda: "")

    def to_dict(self) -> dict:
        return asdict(self, dict_factory=lambda x: {k: v for k, v in x.items() if v is not None})