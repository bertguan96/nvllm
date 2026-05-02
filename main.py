from flask import Flask
from api import register_routes
from service.health import start_background_health_prober

app = Flask(__name__)

register_routes(app)
start_background_health_prober()

if __name__ == '__main__':
    app.run(debug=True)