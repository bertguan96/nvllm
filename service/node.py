from middleware.redis_client import redis_cli
import logging
from model import Response, ResponseMessage, ResponseStatus, ResponseCode, Node

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
            tatus=ResponseStatus.SUCCESS, 
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
        
        
def find_node(trace_id: str) -> Node:
    """
    查找节点
    Args:
        trace_id: Trace ID
    Returns:
        Node object if node found, None otherwise
    """
    try:
        node = redis_cli.hget("nodes", trace_id)
        return Node.from_dict(node)
    except Exception as e:
        logger.error(f"Error finding node: {e}")
        return None 