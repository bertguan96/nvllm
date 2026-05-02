from dataclasses import dataclass, field
import uuid
from datetime import datetime
from typing import Any, Union
import json


@dataclass
class NodeInfo:
    """
    Node info model, used to store node information
    Args:
        running: Running tasks
        waiting: Waiting tasks
        kv_cache: KV cache
    """
    running: int = 0
    waiting: int = 0
    kv_cache: int = 0

    def to_dict(self) -> dict:
        return {
            "running": self.running,
            "waiting": self.waiting,
            "kv_cache": self.kv_cache,
        }

    @classmethod
    def from_dict(cls, data: Union[dict, str]) -> "NodeInfo":
        if isinstance(data, str):
            data = json.loads(data)
        return cls(
            running=int(data.get("running", 0)),
            waiting=int(data.get("waiting", 0)),
            kv_cache=int(data.get("kv_cache", 0)),
        )



@dataclass
class Node:
    """
    Node model, used to store node information
    Args:
        node_id: Node ID (default: random UUID)
        node_type: Node type (required)
        node_address: Node address (required)
        node_port: Node port (required)
        node_status: Node status (default: 'offline')
        served_model_name: OpenAI model id served on this replica (empty = accept any / wildcard pool)
        remark: Remark (default: '')
        create_time: Create time (default: current time)
        update_time: Update time (default: current time)
    """
    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node_type: str = field(default='master')
    node_address: str = field(default='0.0.0.0')
    node_port: int = field(default=8000)
    node_status: str = field(default='offline')
    served_model_name: str = field(default='')
    node_info: NodeInfo = field(default_factory=NodeInfo)
    remark: str = field(default='doc')
    timeout: int = field(default=60)
    create_time: datetime = field(default_factory=datetime.now)
    update_time: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        ct = self.create_time
        ut = self.update_time
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "node_address": self.node_address,
            "node_port": self.node_port,
            "node_status": self.node_status,
            "served_model_name": self.served_model_name,
            "node_info": self.node_info.to_dict(),
            "remark": self.remark,
            "timeout": self.timeout,
            "create_time": ct.isoformat() if isinstance(ct, datetime) else ct,
            "update_time": ut.isoformat() if isinstance(ut, datetime) else ut,
        }

    @classmethod
    def from_dict(cls, data: Union[dict, str, Any]) -> "Node":
        if isinstance(data, str):
            data = json.loads(data)
        if not isinstance(data, dict):
            raise TypeError("Node.from_dict expects dict or JSON string")
        raw_info = data.get("node_info") or {}
        node_info = NodeInfo.from_dict(raw_info) if isinstance(raw_info, (dict, str)) else NodeInfo()

        def _parse_dt(value: Any) -> datetime:
            if value is None:
                return datetime.now()
            if isinstance(value, datetime):
                return value
            if isinstance(value, str):
                try:
                    return datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    return datetime.now()
            return datetime.now()

        return cls(
            node_id=data.get("node_id") or str(uuid.uuid4()),
            node_type=data.get("node_type", "master"),
            node_address=data.get("node_address", "0.0.0.0"),
            node_port=int(data.get("node_port", 8000)),
            node_status=data.get("node_status", "offline"),
            served_model_name=str(data.get("served_model_name", "") or ""),
            node_info=node_info,
            remark=data.get("remark", "doc"),
            timeout=int(data.get("timeout", 60)),
            create_time=_parse_dt(data.get("create_time")),
            update_time=_parse_dt(data.get("update_time")),
        )