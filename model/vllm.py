from dataclasses import dataclass
from enum import Enum
from typing import Any

class VllmStrategy(Enum):
    DEFAULT = "round_robin" # 轮询
    WEIGHTED = "weighted" # 权重
    LEAST_LOAD = "least_load" # 最少负载
    ROUND_ROBIN = "round_robin"
    STREAM = "minimal"  # 最小链接
    RANDOM = "random" # 随机
    SIM_PROMPT = "sim_prompt" # 相似Prompt

class VllmResponseCode(Enum):
    SUCCESS = 0
    ERROR = 1
    TIMEOUT = 2
    INVALID_REQUEST = 3
    INVALID_RESPONSE = 4
    INVALID_PARAMS = 5
    INVALID_MODEL = 6
    INVALID_STRATEGY = 7

class VllmResponseMessage(Enum):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    INVALID_REQUEST = "invalid request"
    INVALID_RESPONSE = "invalid response"
    INVALID_PARAMS = "invalid params"
    INVALID_MODEL = "invalid model"
    INVALID_STRATEGY = "invalid strategy"

@dataclass
class BaseResponse:
    trace_id: str = ""
    code: VllmResponseCode = VllmResponseCode.SUCCESS
    message: VllmResponseMessage = VllmResponseMessage.SUCCESS
    
@dataclass
class BaseRequest:
    trace_id: str = ""
    strategy: str = VllmStrategy.DEFAULT # default, stream, batch
    

@dataclass
class VllmResponse(BaseResponse):
    """
    Vllm response model, used to store response information
    Args:
        info: Info (required)
        trace_id: Trace ID (required)
        data: Data (required)
        err: Error (required)
    """
    info: str = ""
    data: Any = None
    err: str = ""


@dataclass
class VllmRequest(BaseRequest):
    """
    Vllm request model, used to store request information
    Args:
        model: Model (required), to find necessary server
        params: Params (required), to store request parameters
        strategy: Strategy (required)
    """
    model: str
    params: str = ""  # json parms
