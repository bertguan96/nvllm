from dataclasses import dataclass, field
import uuid
from datetime import datetime


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
        remark: Remark (default: '')
        create_time: Create time (default: current time)
        update_time: Update time (default: current time)
    """
    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node_type: str = field(default='master')
    node_address: str = field(default='0.0.0.0')
    node_port: int = field(default=8000)
    node_status: str = field(default='offline')
    remark: str = field(default='doc')
    create_time: datetime = field(default_factory=datetime.now)
    update_time: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        self.create_time = datetime.now()
        self.update_time = datetime.now()
        
    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "node_address": self.node_address,
            "node_port": self.node_port,
            "node_status": self.node_status,
            "remark": self.remark,
            "create_time": self.create_time,
            "update_time": self.update_time,
        }
        
    def from_dict(self, data: str) -> 'Node':
        return Node(**json.loads(data))