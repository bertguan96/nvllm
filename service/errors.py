"""控制面与路由异常（便于 API 层映射 HTTP 状态与运维告警）。"""


class NoBackendError(Exception):
    """
    无可派发的后端副本。
    code 约定：NO_REGISTRY / NO_MODEL_POOL / ALL_UNHEALTHY / TARGET_NOT_FOUND / TARGET_UNHEALTHY
    """

    def __init__(self, message: str, code: str = "NO_BACKEND"):
        super().__init__(message)
        self.code = code
