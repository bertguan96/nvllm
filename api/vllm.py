from flask import Blueprint
from flask import request, jsonify

vllm = Blueprint('vllm', __name__)

@vllm.route('/completions', methods=['POST'])
def completions():
    try:
        data = request.json
        trace_id = request.headers.get('X-Trace-ID')
        response = completions(data, trace_id)
        return jsonify(response.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@vllm.route('/chat/completions', methods=['POST'])
def chat_completions():
    try:
        data = request.json
        trace_id = request.headers.get('X-Trace-ID')
        response = chat_completions(data, trace_id)
        return jsonify(response.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500