import json
import os
from kivy.app import App


def get_session_path():
    app = App.get_running_app()
    user_dir = app.user_data_dir if app else "."
    os.makedirs(user_dir, exist_ok=True)
    return os.path.join(user_dir, "session.json")


def save_session(access_token, refresh_token):
    path = get_session_path()
    data = {"access_token": access_token, "refresh_token": refresh_token}
    with open(path, "w") as f:
        json.dump(data, f)


def load_session():
    path = get_session_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None


def clear_session():
    path = get_session_path()
    if os.path.exists(path):
        os.remove(path)
