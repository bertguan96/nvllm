from flask import Blueprint
from flask import request, jsonify
from middleware.auth import require_jwt
from service import node as node_service
from model import Response, ResponseMessage, ResponseStatus, ResponseCode, Node


node = Blueprint('node', __name__)

@node.route('/node/register', methods=['POST'])
@require_jwt
def register_node():
    try:
        data = request.json
        trace_id = request.headers.get('X-Trace-ID')
        response = node_service.register_node(Node.from_dict(data), trace_id)
        return jsonify(response.to_dict())
    except Exception as e:
        return jsonify(
            Response(message=ResponseMessage.ERROR, 
                     status=ResponseStatus.ERROR, 
                     code=ResponseCode.ERROR, 
                     error=str(e), 
                     trace_id=request.headers.get('X-Trace-ID')).to_dict())



@node.route('/node/update/<node_id>', methods=['PUT'])
@require_jwt
def update_node(node_id):
    try:
        data = request.json or {}
        trace_id = request.headers.get('X-Trace-ID')
        merged = {**data, 'node_id': node_id}
        response = node_service.update_node(Node.from_dict(merged), trace_id)
        return jsonify(response.to_dict())
    except Exception as e:
        return jsonify(
            Response(message=ResponseMessage.ERROR, 
                     status=ResponseStatus.ERROR, 
                     code=ResponseCode.ERROR, 
                     error=str(e), 
                     trace_id=request.headers.get('X-Trace-ID')).to_dict())


@node.route('/node/delete/<node_id>', methods=['DELETE'])
@require_jwt
def delete_node(node_id):
    try:
        trace_id = request.headers.get('X-Trace-ID')
        response = node_service.delete_node(node_id, trace_id)
        return jsonify(response.to_dict())
    except Exception as e:
        return jsonify(
            Response(message=ResponseMessage.ERROR, 
                     status=ResponseStatus.ERROR, 
                     code=ResponseCode.ERROR, 
                     error=str(e), 
                     trace_id=request.headers.get('X-Trace-ID')).to_dict())


@node.route('/node/status/<node_id>', methods=['GET'])
@require_jwt
def get_node_status(node_id):
    try:
        trace_id = request.headers.get('X-Trace-ID')
        response = node_service.get_node_status(node_id, trace_id)
        return jsonify(response.to_dict())
    except Exception as e:
        return jsonify(
            Response(message=ResponseMessage.ERROR, 
                     status=ResponseStatus.ERROR, 
                     code=ResponseCode.ERROR, 
                     error=str(e), 
                     trace_id=request.headers.get('X-Trace-ID')).to_dict())


@node.route('/node/all', methods=['GET'])
@require_jwt
def get_all_nodes():
    try:
        trace_id = request.headers.get('X-Trace-ID')
        response = node_service.get_all_nodes(trace_id)
        return jsonify(response.to_dict())
    except Exception as e:
        return jsonify(
            Response(message=ResponseMessage.ERROR, 
                     status=ResponseStatus.ERROR, 
                     code=ResponseCode.ERROR, 
                     error=str(e), 
                     trace_id=request.headers.get('X-Trace-ID')).to_dict())

@node.route('/node/get_node/<node_id>', methods=['GET'])
@require_jwt
def get_node(node_id):
    try:
        trace_id = request.headers.get('X-Trace-ID')
        response = node_service.get_node(node_id, trace_id)
        return jsonify(response.to_dict())
    except Exception as e:
        return jsonify(
            Response(
                message=ResponseMessage.ERROR, 
                status=ResponseStatus.ERROR, 
                code=ResponseCode.ERROR, 
                error=str(e), 
                trace_id=request.headers.get('X-Trace-ID')).to_dict()
            )
    
