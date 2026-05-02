from flask import Blueprint
from flask import request, jsonify, Response

from service.errors import NoBackendError
from service import vllm as vllm_service

vllm = Blueprint('vllm', __name__)

_HTTP_FOR_CODE = {
    "NO_REGISTRY": 503,
    "NO_MODEL_POOL": 503,
    "ALL_UNHEALTHY": 503,
    "TARGET_NOT_FOUND": 404,
    "TARGET_UNHEALTHY": 503,
    "NO_BACKEND": 503,
}


def _handle_forward(path: str):
    body = request.get_json(silent=True)
    result = vllm_service.forward_openai(path, body, request.headers)
    if isinstance(result, Response):
        return result
    data, status = result
    return jsonify(data), status


@vllm.route('/completions', methods=['POST'])
def completions_route():
    try:
        return _handle_forward('/v1/completions')
    except NoBackendError as e:
        payload = {"error": str(e), "code": e.code}
        return jsonify(payload), _HTTP_FOR_CODE.get(e.code, 503)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@vllm.route('/chat/completions', methods=['POST'])
def chat_completions_route():
    try:
        return _handle_forward('/v1/chat/completions')
    except NoBackendError as e:
        payload = {"error": str(e), "code": e.code}
        return jsonify(payload), _HTTP_FOR_CODE.get(e.code, 503)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
