from flask import Flask
from flask_socketio import SocketIO
from app.api.controllers.product_controller import product_api
from app.graphql.schema import schema
from flask_graphql import GraphQLView
from app.socket.events import on_connect
from configurations import app_config

def create_app(config):
    app = Flask(__name__)

    app.config.from_object(app_config)

    app.register_blueprint(product_api)

    app.add_url_rule(
        "/graphql",
        view_func=GraphQLView.as_view("graphql", schema=schema, graphiql=True),
    )

    socketio = SocketIO(app, cors_allowed_origins="*")
    socketio.on("connect")(on_connect)
    return app, socketio
