from flask_socketio import send
from app.shared.constants import HELLO_MESSAGE

def on_connect():
    send(HELLO_MESSAGE)
