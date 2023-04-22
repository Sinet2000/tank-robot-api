import os
from app import create_app
from flask_socketio import SocketIO

if __name__ == "__main__":
    os.environ.setdefault("APP_ENV", "development")
    app, socketio = create_app()
    socketio.run(app)
