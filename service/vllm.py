import logging
import os
from typing import Any, Dict, Optional, Tuple, Union

import requests
from flask import Response, stream_with_context

from service.health import invalidate_node
from service.node import ordered_inference_candidates

logger = logging.getLogger(__name__)

# 连接失败、上游 5xx 时最多尝试的副本数（含首轮）
UPSTREAM_MAX_TRIES = max(1, int(os.environ.get("NVLLM_UPSTREAM_MAX_TRIES", "3")))

# 非流式响应中视为可换副本重试的 HTTP 状态
_RETRY_UPSTREAM_STATUS = {500, 502, 503, 504}


def _base_url(node: Any) -> str:
    return f"http://{node.node_address}:{node.node_port}"


def forward_openai(
    path: str,
    body: Optional[Dict[str, Any]],
    headers,
) -> Union[Response, Tuple[Any, int]]:
    """
    将 OpenAI 兼容请求转发到选中的 vLLM 节点；支持候选链路与运维级重试。
    """
    target = headers.get("X-Target-Node-Id") or headers.get("X-Target-Node-ID")
    trace_id = headers.get("X-Trace-ID")
    candidates = ordered_inference_candidates(
        target_node_id=target,
        trace_id=trace_id,
        body=body,
        headers=headers,
    )

    stream = bool(body and body.get("stream"))
    max_tries = min(UPSTREAM_MAX_TRIES, len(candidates))
    last_err: str = "no attempt made"

    for i, node in enumerate(candidates[:max_tries]):
        url = f"{_base_url(node)}{path}"
        timeout = float(node.timeout or 60)
        fwd_headers = {"Content-Type": "application/json"}
        auth = headers.get("Authorization")
        if auth:
            fwd_headers["Authorization"] = auth

        try:
            r = requests.post(
                url,
                json=body,
                headers=fwd_headers,
                timeout=timeout,
                stream=stream,
            )
        except requests.RequestException as e:
            last_err = str(e)
            logger.warning(
                "upstream unreachable node=%s url=%s err=%s",
                node.node_id,
                url,
                e,
            )
            invalidate_node(node.node_id)
            continue

        if stream:
            if r.status_code in _RETRY_UPSTREAM_STATUS:
                r.close()
                last_err = r.text or f"upstream status {r.status_code}"
                logger.warning(
                    "upstream 5xx stream node=%s status=%s", node.node_id, r.status_code
                )
                invalidate_node(node.node_id)
                continue

            def generate():
                try:
                    for chunk in r.iter_content(chunk_size=None):
                        if chunk:
                            yield chunk
                finally:
                    r.close()

            return Response(
                stream_with_context(generate()),
                status=r.status_code,
                mimetype=r.headers.get("Content-Type", "text/event-stream"),
            )

        if 400 <= r.status_code < 500:
            try:
                return r.json(), r.status_code
            except ValueError:
                return {"error": r.text or "upstream client error"}, r.status_code

        if r.status_code in _RETRY_UPSTREAM_STATUS:
            try:
                last_err = str(r.json())
            except ValueError:
                last_err = r.text or f"status {r.status_code}"
            logger.warning(
                "upstream 5xx node=%s status=%s", node.node_id, r.status_code
            )
            invalidate_node(node.node_id)
            continue

        try:
            return r.json(), r.status_code
        except ValueError:
            text = r.text or "invalid upstream response"
            return {"error": text}, r.status_code

    return (
        {
            "error": "all upstream replicas failed",
            "detail": last_err,
        },
        502,
    )
