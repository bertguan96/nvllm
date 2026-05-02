from middleware.redis_client import redis_cli
import logging
from typing import Any, Dict, List, Mapping, Optional

from model import Response, ResponseMessage, ResponseStatus, ResponseCode, Node

from service.errors import NoBackendError
from service.health import HEALTH_ENABLED, HEALTH_FALLBACK, node_is_healthy
from service.routing import (
    filter_pool_by_requested_model,
    node_load,
    requested_openai_model,
    select_replica_jsq_with_prefix_affinity,
)

logger = logging.getLogger(__name__)

def register_node(node: Node, trace_id: str) -> Response:
    """
    注册节点
    Args:
        node: Node object
    Returns:
        {"message": "Node registered successfully", "status": "success", "code": 200} if node registered successfully, {"error": str(e), "status": "error", "code": 500} otherwise
    """
    try:
        redis_cli.hset("nodes", node.node_id, node.to_dict())
        return Response(
            message=ResponseMessage.SUCCESS,
            status=ResponseStatus.SUCCESS,
            code=ResponseCode.SUCCESS,
            data=node.to_dict(),
            trace_id=trace_id)
    except Exception as e:
        logger.error(f"trace_id: {trace_id} Error registering node: {e}")
        return Response(
            message=ResponseMessage.ERROR, 
            status=ResponseStatus.ERROR, 
            code=ResponseCode.ERROR, 
            error=str(e),
            trace_id=trace_id)
    
    
def get_all_nodes(trace_id: str) -> Response:
    """
    获取所有节点
    Args:
        None
    Returns:
        Response object if nodes retrieved successfully, Response object with error message otherwise
    """
    try:
        nodes = redis_cli.hgetall("nodes")
        return Response(
            message=ResponseMessage.SUCCESS, 
            status=ResponseStatus.SUCCESS, 
            code=ResponseCode.SUCCESS, 
            data=[Node.from_dict(node) for node in nodes.values()],
            trace_id=trace_id)
    except Exception as e:
        logger.error(f"Error getting node: {e}")
        return Response(
            message=ResponseMessage.ERROR, 
            status=ResponseStatus.ERROR, 
            code=ResponseCode.ERROR, 
            error=str(e),
            trace_id=trace_id)
    
def get_node(node_id: str, trace_id: str) -> Response:
    """
    获取一个节点
    Args:
        node_id: Node ID
    Returns:
        Node object if node retrieved successfully, None otherwise
    """
    try:
        node = redis_cli.hget("nodes", node_id)
        if node is None:
            return Response(
                message=ResponseMessage.NOT_FOUND,
                status=ResponseStatus.NOT_FOUND,
                code=ResponseCode.NOT_FOUND,
                error="node not found",
                trace_id=trace_id,
            )
        return Response(
            message=ResponseMessage.SUCCESS, 
            status=ResponseStatus.SUCCESS, 
            code=ResponseCode.SUCCESS, 
            data=Node.from_dict(node),
            trace_id=trace_id)
    except Exception as e:
        logger.error(f"trace_id: {trace_id} Error getting node: {e}")
        return Response(
            message=ResponseMessage.ERROR, 
            status=ResponseStatus.ERROR, 
            code=ResponseCode.ERROR, 
            error=str(e),
            trace_id=trace_id)
    
    
def update_node(node: Node, trace_id: str) -> Response:
    """
    更新节点
    Args:
        node: Node object
    Returns:
        {"message": "Node updated successfully", "status": "success", "code": 200} if node updated successfully, {"error": str(e), "status": "error", "code": 500} otherwise
    """
    try:
        redis_cli.hset("nodes", node.node_id, node.to_dict())
        return Response(
            message=ResponseMessage.SUCCESS, 
            status=ResponseStatus.SUCCESS, 
            code=ResponseCode.SUCCESS, 
            data=node.to_dict(),
            trace_id=trace_id)
    except Exception as e:
        logger.error(f"trace_id: {trace_id} Error updating node: {e}")
        return Response(
            message=ResponseMessage.ERROR, 
            status=ResponseStatus.ERROR, 
            code=ResponseCode.ERROR, 
            error=str(e),
            trace_id=trace_id)
    
def delete_node(node_id: str, trace_id: str) -> Response:
    """
    删除节点
    Args:
        node_id: Node ID
    Returns:
        {"message": "Node deleted successfully", "status": "success", "code": 200} if node deleted successfully, {"error": str(e), "status": "error", "code": 500} otherwise    
    """
    try:
        redis_cli.hdel("nodes", node_id)
        return Response(
            message=ResponseMessage.SUCCESS, 
            status=ResponseStatus.SUCCESS, 
            code=ResponseCode.SUCCESS, 
            data=node_id,
            trace_id=trace_id)
    except Exception as e:
        logger.error(f"trace_id: {trace_id} Error deleting node: {e}")
        return Response(
            message=ResponseMessage.ERROR, 
            status=ResponseStatus.ERROR, 
            code=ResponseCode.ERROR, 
            error=str(e),
            trace_id=trace_id)
    
def get_node_status(node_id: str, trace_id: str) -> Response:
    """
    获取节点状态
    Args:
        node_id: Node ID
    Returns:
        Response object if node status retrieved successfully, Response object with error message otherwise
    """
    try:
        node = redis_cli.hget("nodes", node_id)
        if node is None:
            return Response(
                message=ResponseMessage.NOT_FOUND,
                status=ResponseStatus.NOT_FOUND,
                code=ResponseCode.NOT_FOUND,
                error="node not found",
                trace_id=trace_id,
            )
        return Response(
            message=ResponseMessage.SUCCESS, 
            status=ResponseStatus.SUCCESS, 
            code=ResponseCode.SUCCESS, 
            data=Node.from_dict(node),
            trace_id=trace_id)
    except Exception as e:
        logger.error(f"Error getting node status: {e}")
        return Response(
            message=ResponseMessage.ERROR, 
            status=ResponseStatus.ERROR, 
            code=ResponseCode.ERROR, 
            error=str(e),
            trace_id=trace_id)
        
def _nodes_from_redis() -> List[Node]:
    raw = redis_cli.hgetall("nodes")
    out = []
    for v in raw.values():
        try:
            out.append(Node.from_dict(v))
        except (TypeError, ValueError, KeyError) as e:
            logger.warning("skip invalid node record: %s", e)
    return out


def ordered_inference_candidates(
    target_node_id: Optional[str],
    trace_id: Optional[str],
    body: Optional[Dict[str, Any]] = None,
    headers: Optional[Mapping[str, str]] = None,
) -> List[Node]:
    """
    返回按优先级排序的副本列表：亲和/JSQ 首选在前，其余按负载升序，供上游故障重试。
    """
    if target_node_id:
        raw = redis_cli.hget("nodes", target_node_id)
        if not raw:
            raise NoBackendError(
                f"target node {target_node_id} not found",
                "TARGET_NOT_FOUND",
            )
        try:
            node = Node.from_dict(raw)
        except (TypeError, ValueError, KeyError) as e:
            logger.error("resolve_backend_node by id failed: %s", e)
            raise NoBackendError(
                f"target node {target_node_id} invalid record",
                "TARGET_NOT_FOUND",
            ) from e
        if HEALTH_ENABLED and not node_is_healthy(node):
            raise NoBackendError(
                f"target node {target_node_id} failed health check",
                "TARGET_UNHEALTHY",
            )
        return [node]

    if trace_id:
        raw = redis_cli.hget("nodes", trace_id)
        if raw:
            try:
                node = Node.from_dict(raw)
                if not HEALTH_ENABLED or node_is_healthy(node):
                    return [node]
                logger.warning(
                    "sticky node %s unhealthy, failing over to pool",
                    trace_id,
                )
            except (TypeError, ValueError, KeyError):
                pass

    candidates = _nodes_from_redis()
    if not candidates:
        raise NoBackendError("no nodes registered in catalog", "NO_REGISTRY")

    online = [n for n in candidates if n.node_status == "online"]
    pool = online if online else candidates
    req_model = requested_openai_model(body, headers)
    pool = filter_pool_by_requested_model(pool, req_model)
    if not pool:
        raise NoBackendError(
            "no replica matches requested model",
            "NO_MODEL_POOL",
        )

    if HEALTH_ENABLED:
        healthy = [n for n in pool if node_is_healthy(n)]
        if healthy:
            pool = healthy
        elif HEALTH_FALLBACK:
            logger.warning(
                "all candidates failed health check, using catalog pool (fallback)",
            )
        else:
            raise NoBackendError(
                "all replicas failed health check",
                "ALL_UNHEALTHY",
            )

    primary = select_replica_jsq_with_prefix_affinity(pool, body)
    if primary is None:
        raise NoBackendError("could not select replica", "NO_REGISTRY")
    others = sorted(
        [n for n in pool if n.node_id != primary.node_id],
        key=node_load,
    )
    return [primary] + others


def resolve_backend_node(
    target_node_id: Optional[str],
    trace_id: Optional[str],
    body: Optional[Dict[str, Any]] = None,
    headers: Optional[Mapping[str, str]] = None,
) -> Optional[Node]:
    """
    返回单个首选副本；失败时返回 None（兼容旧调用方）。
    """
    try:
        return ordered_inference_candidates(
            target_node_id, trace_id, body, headers
        )[0]
    except NoBackendError:
        return None


def find_node(trace_id: str) -> Optional[Node]:
    """兼容旧接口：无请求体时仅 JSQ + trace 解析。"""
    return resolve_backend_node(None, trace_id, body=None, headers=None)