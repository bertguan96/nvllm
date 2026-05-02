"""
大规模推理入口：前缀亲和（稳定哈希）+ 最短队列回退（JSQ）。

- 同前缀请求稳定映射到同一副本，利于 prefix KV 局部性；
- 当亲和副本负载高于全局最小负载超过 margin 时，改派到负载最低副本，避免热点。
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any, Dict, List, Mapping, Optional

from model.node import Node

logger = logging.getLogger(__name__)

# 参与哈希的文本上限（字节级局部性，与引擎 prefix cache 常见尺度同量级可调）
PREFIX_MAX_CHARS = int(os.environ.get("NVLLM_ROUTING_PREFIX_CHARS", "8192"))

# 亲和副本允许比全局 min_load 高出的「在途量」上限，超过则 JSQ 回退
AFFINITY_LOAD_MARGIN = int(os.environ.get("NVLLM_AFFINITY_LOAD_MARGIN", "2"))


def _node_load(n: Node) -> int:
    return int(n.node_info.running) + int(n.node_info.waiting)


def node_load(n: Node) -> int:
    """对外暴露的负载标量，供排序与重试顺序使用。"""
    return _node_load(n)


def openai_routing_key(body: Optional[Dict[str, Any]]) -> str:
    """
    从 OpenAI 兼容 body 提取用于路由的稳定前缀文本。
    无 messages/prompt 时用 sort_keys JSON 截断，避免各网关字段顺序不一致。
    """
    if not body:
        return ""
    try:
        if "messages" in body:
            parts: List[str] = []
            for m in body.get("messages") or []:
                if not isinstance(m, dict):
                    continue
                c = m.get("content")
                if isinstance(c, str):
                    parts.append(c)
                elif isinstance(c, list):
                    for p in c:
                        if isinstance(p, dict) and p.get("type") == "text":
                            parts.append(str(p.get("text", "")))
            s = "\n".join(parts)
        elif "prompt" in body:
            p = body["prompt"]
            s = p if isinstance(p, str) else str(p)
        else:
            s = json.dumps(body, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError) as e:
        logger.debug("openai_routing_key fallback: %s", e)
        s = json.dumps(body, ensure_ascii=False, sort_keys=True)
    s = s.strip()
    if len(s) > PREFIX_MAX_CHARS:
        s = s[:PREFIX_MAX_CHARS]
    return s


def requested_openai_model(
    body: Optional[Dict[str, Any]],
    headers: Optional[Mapping[str, str]],
) -> Optional[str]:
    """来自 OpenAI body.model，或由网关补充的头（如无 body）。"""
    if body:
        m = body.get("model")
        if isinstance(m, str) and m.strip():
            return m.strip()
    if not headers:
        return None
    for key in ("X-Route-Model", "X-OpenAI-Model"):
        h = headers.get(key)
        if h and str(h).strip():
            return str(h).strip()
    return None


def filter_pool_by_requested_model(
    pool: List[Node],
    requested_model: Optional[str],
) -> List[Node]:
    """
    - 请求未带 model：优先使用 served_model_name 为空的「通用池」；若无则退回全池（兼容旧节点）。
    - 请求带 model：仅保留 served_model_name 与该 model 一致的副本；不做跨模型降级。
    """
    if not pool:
        return pool
    rm = (requested_model or "").strip()
    if not rm:
        wild = [n for n in pool if not (n.served_model_name or "").strip()]
        return wild if wild else pool
    return [n for n in pool if (n.served_model_name or "").strip() == rm]


def _stable_bucket(key: str, n_slots: int) -> int:
    if n_slots <= 0:
        return 0
    h = hashlib.sha256(key.encode("utf-8")).digest()[:8]
    return int.from_bytes(h, "big", signed=False) % n_slots


def select_replica_jsq_with_prefix_affinity(
    pool: List[Node],
    body: Optional[Dict[str, Any]],
) -> Optional[Node]:
    """
    在 pool 上先做稳定排序，再按前缀哈希选槽位；若该槽负载明显高于全局最短路则回退到 JSQ。
    """
    if not pool:
        return None
    if len(pool) == 1:
        return pool[0]

    ordered = sorted(pool, key=lambda n: n.node_id)
    key = openai_routing_key(body)
    if not key:
        return min(ordered, key=_node_load)

    idx = _stable_bucket(key, len(ordered))
    primary = ordered[idx]
    loads = [_node_load(n) for n in ordered]
    min_load = min(loads)
    if _node_load(primary) <= min_load + AFFINITY_LOAD_MARGIN:
        return primary
    best = min(ordered, key=_node_load)
    if best.node_id != primary.node_id:
        logger.debug(
            "routing jsq fallback primary=%s load=%s min_load=%s margin=%s -> %s",
            primary.node_id,
            _node_load(primary),
            min_load,
            AFFINITY_LOAD_MARGIN,
            best.node_id,
        )
    return best
