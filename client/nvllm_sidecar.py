#!/usr/bin/env python3
"""
nvllm 侧上报脚本：向 nvllm 控制面登录、注册节点并周期性 PUT 更新 node_info。

部署：与本机 vLLM 同机或同网络，安装依赖后后台运行：

  pip install -r requirements.txt
  export NVLLM_CONTROL_PLANE_URL=http://nvllm-gateway:5000
  export NVLLM_NODE_ID=gpu-01
  export NVLLM_NODE_ADDRESS=10.0.0.12
  export NVLLM_NODE_PORT=8000
  export NVLLM_SERVED_MODEL_NAME=meta-llama/Llama-3.1-8B-Instruct
  python nvllm_sidecar.py

可选：设置 NVLLM_VLLM_METRICS_URL=http://127.0.0.1:8000/metrics 从 Prometheus 文本抓取
running/waiting（匹配常见 vLLM 指标名）；未设置则使用固定数值或全 0。
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from typing import Any, Dict, Optional, Tuple

import requests

logger = logging.getLogger("nvllm_sidecar")


def _env(name: str, default: Optional[str] = None) -> str:
    v = os.environ.get(name, default)
    if v is None or v == "":
        raise RuntimeError(f"missing required env: {name}")
    return v


def _parse_metrics(text: str) -> Tuple[int, int, int]:
    """
    从 Prometheus 文本中解析 running / waiting / kv_cache。
    优先匹配 vLLM 常见指标名；解析失败则返回 (0,0,0)。
    """
    running = waiting = kv = 0
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        metric = parts[0]
        try:
            val = int(float(parts[-1]))
        except ValueError:
            continue
        if "num_requests_running" in metric or metric.endswith("_requests_running"):
            running = val
        elif "num_requests_waiting" in metric or metric.endswith("_requests_waiting"):
            waiting = val
        elif "kv_cache" in metric.lower() and "usage" in metric.lower():
            kv = val
    return running, waiting, kv


def _fetch_metrics(url: str, timeout: float) -> Tuple[int, int, int]:
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return _parse_metrics(r.text)


def _extract_token(payload: Dict[str, Any]) -> str:
    data = payload.get("data")
    if isinstance(data, dict) and data.get("token"):
        return str(data["token"])
    if payload.get("token"):
        return str(payload["token"])
    raise KeyError("token not found in login response: %s" % payload)


class Sidecar:
    def __init__(self) -> None:
        self.base = os.environ["NVLLM_CONTROL_PLANE_URL"].rstrip("/")
        self.username = os.environ.get("NVLLM_USERNAME", "admin")
        self.password = os.environ.get("NVLLM_PASSWORD")  # 预留，当前登录接口未校验密码
        self.node_id = _env("NVLLM_NODE_ID")
        self.node_address = _env("NVLLM_NODE_ADDRESS")
        self.node_port = int(os.environ.get("NVLLM_NODE_PORT", "8000"))
        self.node_type = os.environ.get("NVLLM_NODE_TYPE", "worker")
        self.served_model = os.environ.get("NVLLM_SERVED_MODEL_NAME", "")
        self.node_status = os.environ.get("NVLLM_NODE_STATUS", "online")
        self.timeout_sec = int(os.environ.get("NVLLM_HTTP_TIMEOUT_SEC", "30"))
        self.interval = float(os.environ.get("NVLLM_REPORT_INTERVAL_SEC", "10"))
        self.metrics_url = os.environ.get("NVLLM_VLLM_METRICS_URL")
        self.metrics_timeout = float(os.environ.get("NVLLM_METRICS_TIMEOUT_SEC", "3"))
        self.skip_register = os.environ.get("NVLLM_SKIP_REGISTER", "").lower() in (
            "1",
            "true",
            "yes",
        )
        self.token_refresh_sec = float(
            os.environ.get("NVLLM_TOKEN_REFRESH_SEC", "3300")
        )  # < 典型 JWT 1h

        self._session = requests.Session()
        self._token: Optional[str] = None
        self._token_obtained_at = 0.0

    def _need_refresh_token(self) -> bool:
        if not self._token:
            return True
        return (time.time() - self._token_obtained_at) >= self.token_refresh_sec

    def login(self) -> None:
        url = f"{self.base}/api/user/login"
        body: Dict[str, Any] = {"username": self.username}
        if self.password:
            body["password"] = self.password
        r = self._session.post(
            url,
            json=body,
            timeout=self.timeout_sec,
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()
        payload = r.json()
        self._token = _extract_token(payload)
        self._token_obtained_at = time.time()
        logger.info("login ok user=%s", self.username)

    def _auth_headers(self) -> Dict[str, str]:
        if self._need_refresh_token():
            self.login()
        assert self._token
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    def register(self) -> None:
        url = f"{self.base}/api/node/node/register"
        body = {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "node_address": self.node_address,
            "node_port": self.node_port,
            "node_status": self.node_status,
            "served_model_name": self.served_model,
            "node_info": {"running": 0, "waiting": 0, "kv_cache": 0},
            "remark": os.environ.get("NVLLM_NODE_REMARK", "nvllm_sidecar"),
            "timeout": int(os.environ.get("NVLLM_NODE_TIMEOUT_SEC", "120")),
        }
        r = self._session.post(
            url, json=body, headers=self._auth_headers(), timeout=self.timeout_sec
        )
        if r.status_code >= 400:
            logger.warning("register returned %s: %s", r.status_code, r.text[:500])
            r.raise_for_status()
        logger.info("register ok node_id=%s", self.node_id)

    def _collect_node_info(self) -> Dict[str, int]:
        if self.metrics_url:
            try:
                running, waiting, kv = _fetch_metrics(
                    self.metrics_url, self.metrics_timeout
                )
                return {"running": running, "waiting": waiting, "kv_cache": kv}
            except Exception as e:
                logger.warning("metrics scrape failed, using env fallback: %s", e)
        # 静态兜底（无 metrics 或抓取失败）
        return {
            "running": int(os.environ.get("NVLLM_NODE_INFO_RUNNING", "0")),
            "waiting": int(os.environ.get("NVLLM_NODE_INFO_WAITING", "0")),
            "kv_cache": int(os.environ.get("NVLLM_NODE_INFO_KV_CACHE", "0")),
        }

    def update(self) -> None:
        url = f"{self.base}/api/node/node/update/{self.node_id}"
        body: Dict[str, Any] = {
            "node_status": self.node_status,
            "node_info": self._collect_node_info(),
        }
        # 允许顺带刷新可达地址（例如弹性网卡变更）
        if os.environ.get("NVLLM_UPDATE_ADDRESS", "").lower() in ("1", "true", "yes"):
            body["node_address"] = self.node_address
            body["node_port"] = self.node_port
        if os.environ.get("NVLLM_UPDATE_MODEL", "").lower() in ("1", "true", "yes"):
            body["served_model_name"] = self.served_model

        r = self._session.put(
            url, json=body, headers=self._auth_headers(), timeout=self.timeout_sec
        )
        if r.status_code == 401:
            self.login()
            r = self._session.put(
                url, json=body, headers=self._auth_headers(), timeout=self.timeout_sec
            )
        r.raise_for_status()
        logger.debug("update ok %s", body.get("node_info"))

    def run_forever(self) -> None:
        self.login()
        if not self.skip_register:
            self.register()
        while True:
            try:
                self.update()
            except requests.HTTPError as e:
                logger.error("update failed: %s %s", e, getattr(e.response, "text", ""))
            except Exception:
                logger.exception("update loop error")
            time.sleep(self.interval)


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("NVLLM_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    p = argparse.ArgumentParser(description="nvllm control plane sidecar")
    p.add_argument(
        "--once",
        action="store_true",
        help="login [register] update once then exit (for cron)",
    )
    args = p.parse_args()

    try:
        os.environ["NVLLM_CONTROL_PLANE_URL"]
    except KeyError:
        logger.error("NVLLM_CONTROL_PLANE_URL is required")
        return 2

    sidecar = Sidecar()
    sidecar.login()
    if args.once:
        if not sidecar.skip_register:
            sidecar.register()
        sidecar.update()
        logger.info("once mode done")
        return 0

    sidecar.run_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
