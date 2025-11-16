from flask import Blueprint, Flask
from .node import node
from .user import user
from .vllm import vllm

# define route list
# - router: the router object
# - prefix: the prefix of the router
# - name: the name of the router
router_list = [
    {
        'router': user,
        'prefix': '/api/user',
        'name': 'user',
    },
    {
        'router': node,
        'prefix': '/api/node',
        'name': 'node',
    },
    {
        'router': vllm,
        'prefix': '/v1',
        'name': 'vllm',
    }
]
def register_routes(app: Flask):
    # register routes
    for router_info in router_list:
        router = router_info['router']
        prefix = router_info['prefix']
        name = router_info['name']
        print(f"Registering router {name} with prefix {prefix}")
        app.register_blueprint(router, url_prefix=prefix)