from flask import Blueprint, request, jsonify
from middleware.auth import generate_token
from model import Response, ResponseMessage, ResponseStatus, ResponseCode

user = Blueprint('user', __name__)

@user.route('/login', methods=['POST'])
def login():
    username = request.json.get('username')
    if username in ["admin", "user"]:
        token = generate_token(username)
        return jsonify(
            Response(
                message=ResponseMessage.SUCCESS, 
                status=ResponseStatus.SUCCESS, 
                code=ResponseCode.SUCCESS, 
                data={"token": token}, 
                trace_id=request.headers.get('X-Trace-ID')
            ).to_dict()
        )
        
    return jsonify(
        Response(
            message=ResponseMessage.ERROR, 
            status=ResponseStatus.ERROR, 
            code=ResponseCode.ERROR, 
            error=ResponseMessage.UNAUTHORIZED, 
            trace_id=request.headers.get('X-Trace-ID')).to_dict()
        )
    