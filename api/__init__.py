from flask import Blueprint, Flask
from .node import node
from .user import user


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
]
def register_routes(app: Flask):
    for router_info in router_list:
        router = router_info['router']
        prefix = router_info['prefix']
        name = router_info['name']
        print(f"Registering router {name} with prefix {prefix}")
        app.register_blueprint(router, url_prefix=prefix)