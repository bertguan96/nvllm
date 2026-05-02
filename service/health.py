"""
副本存活探测（HTTP GET）；结果写入 Redis；探测路径使用分布式锁，避免多网关同时打同一副本。

可选后台线程按间隔主动刷新（心跳），与请求路径共用同一锁与缓存。
"""
from __future__ import annotations

import logging
import os
import threading
import time
from typing import Optional

import requests

from middleware.redis_client import redis_cli

logger = logging.getLogger(__name__)

HEALTH_ENABLED = os.environ.get("NVLLM_HEALTH_CHECK", "0").lower() in (
    "1",
    "true",
    "yes",
)
HEALTH_PATH = os.environ.get("NVLLM_HEALTH_PATH", "/health")
HEALTH_CACHE_SEC = float(os.environ.get("NVLLM_HEALTH_CACHE_SEC", "5"))
HEALTH_TIMEOUT = float(os.environ.get("NVLLM_HEALTH_TIMEOUT_SEC", "2"))
HEALTH_FALLBACK = os.environ.get("NVLLM_HEALTH_FALLBACK", "1").lower() in (
    "1",
    "true",
    "yes",
)

HEALTH_REDIS_PREFIX = os.environ.get("NVLLM_HEALTH_REDIS_PREFIX", "nvllm:health:")
LOCK_PREFIX = os.environ.get("NVLLM_HEALTH_LOCK_PREFIX", "nvllm:health:lock:")
PROBE_LOCK_SEC = int(os.environ.get("NVLLM_HEALTH_PROBE_LOCK_SEC", "5"))

# 未抢到锁时轮询 Redis 结果：次数 × 间隔 ≈ 最长等待
LOCK_WAIT_ITERATIONS = int(os.environ.get("NVLLM_HEALTH_LOCK_WAIT_ITERATIONS", "20"))
LOCK_WAIT_SLEEP_SEC = float(os.environ.get("NVLLM_HEALTH_LOCK_WAIT_MS", "50")) / 1000.0

HEALTH_INVALIDATE_SEC = int(
    os.environ.get(
        "NVLLM_HEALTH_INVALIDATE_SEC",
        str(max(10, int(HEALTH_CACHE_SEC))),
    )
)

# >0 时启动守护线程，周期性拉 catalog 并 force 刷新（仍走分布式锁）
HEALTH_BG_INTERVAL_SEC = float(os.environ.get("NVLLM_HEALTH_BG_INTERVAL_SEC", "0"))


def _key(node_id: str) -> str:
    return f"{HEALTH_REDIS_PREFIX}{node_id}"


def _lock_key(node_id: str) -> str:
    return f"{LOCK_PREFIX}{node_id}"


def _ttl_cache_seconds() -> int:
    return max(1, int(HEALTH_CACHE_SEC))


def _norm_cached_ok(value) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("1", "true", "yes", "ok", "up"):
            return True
        if v in ("0", "false", "no", "down"):
            return False
    return None


def invalidate_node(node_id: str) -> None:
    k = _key(node_id)
    ex = max(_ttl_cache_seconds(), HEALTH_INVALIDATE_SEC)
    if not redis_cli.set(k, "0", ex=ex):
        logger.warning("redis set failed for health invalidate node=%s", node_id)


def _probe_http(node) -> bool:
    url = f"http://{node.node_address}:{node.node_port}{HEALTH_PATH}"
    try:
        r = requests.get(url, timeout=HEALTH_TIMEOUT)
        return r.status_code < 500
    except requests.RequestException as e:
        logger.debug("health check failed %s: %s", url, e)
        return False


def _probe_and_publish(node) -> bool:
    ok = _probe_http(node)
    redis_cli.set(_key(node.node_id), "1" if ok else "0", ex=_ttl_cache_seconds())
    return ok


def _try_acquire_probe_lock(node_id: str) -> bool:
    try:
        return bool(
            redis_cli.client.set(
                _lock_key(node_id),
                "1",
                nx=True,
                ex=max(1, PROBE_LOCK_SEC),
            )
        )
    except Exception as e:
        logger.warning("redis probe lock acquire failed: %s", e)
        return False


def _release_probe_lock(node_id: str) -> None:
    try:
        redis_cli.delete(_lock_key(node_id))
    except Exception:
        pass


def node_is_healthy(node, force_refresh: bool = False) -> bool:
    """
    force_refresh=True 时跳过读缓存（用于后台心跳），仍通过分布式锁与其它实例协调探测。
    """
    if not HEALTH_ENABLED:
        return True

    k = _key(node.node_id)
    if not force_refresh:
        cached = redis_cli.get(k)
        ok_cached = _norm_cached_ok(cached)
        if ok_cached is not None:
            return ok_cached

    if _try_acquire_probe_lock(node.node_id):
        try:
            return _probe_and_publish(node)
        finally:
            _release_probe_lock(node.node_id)

    for _ in range(LOCK_WAIT_ITERATIONS):
        time.sleep(LOCK_WAIT_SLEEP_SEC)
        cached = redis_cli.get(k)
        ok_cached = _norm_cached_ok(cached)
        if ok_cached is not None:
            return ok_cached

    logger.warning(
        "health probe lock wait exhausted node=%s, probing without lock",
        node.node_id,
    )
    return _probe_and_publish(node)


_bg_started = False
_bg_lock = threading.Lock()


def _background_health_loop() -> None:
    while True:
        try:
            interval = HEALTH_BG_INTERVAL_SEC
            if interval <= 0:
                return
            time.sleep(interval)
            from service.node import _nodes_from_redis

            nodes = _nodes_from_redis()
            for node in nodes:
                try:
                    node_is_healthy(node, force_refresh=True)
                except Exception:
                    logger.exception("bg health probe failed node=%s", node.node_id)
        except Exception:
            logger.exception("bg health iteration failed")


def start_background_health_prober() -> None:
    """在进程启动时调用：若 NVLLM_HEALTH_BG_INTERVAL_SEC>0 且启用健康检查则启动守护线程。"""
    global _bg_started
    if HEALTH_BG_INTERVAL_SEC <= 0 or not HEALTH_ENABLED:
        return
    with _bg_lock:
        if _bg_started:
            return
        t = threading.Thread(
            target=_background_health_loop,
            daemon=True,
            name="nvllm-health-bg",
        )
        t.start()
        _bg_started = True
        logger.info(
            "background health prober started interval_sec=%s",
            HEALTH_BG_INTERVAL_SEC,
        )
