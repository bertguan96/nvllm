from .node import find_node

def completions(data: dict, trace_id: str, route: str) -> dict:
    """
    completions api
    @param data: the data of the request
    @param trace_id: the trace id of the request
    @param route: the route of the request, v1/completions or v1/chat/completions
    @return: the response of the request
    """
    try:
        # find the node
        node = find_node(trace_id)
        if route == 'v1/completions':
            return completions(data, trace_id)
        elif route == 'v1/chat/completions':
            return chat_completions(data, trace_id)
        else:
            return jsonify({'error': 'invalid route'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500