import os
import pytest

from collab.server import create_app


@pytest.fixture()
def tmp_data_dir(tmp_path):
    return tmp_path / "data"


@pytest.fixture()
def app_socket_store(tmp_data_dir, monkeypatch):
    # ensure clean data dir
    os.makedirs(tmp_data_dir, exist_ok=True)
    app, socketio, store = create_app(testing=True, data_dir=str(tmp_data_dir))
    return app, socketio, store


@pytest.fixture()
def client_factory(app_socket_store):
    app, socketio, store = app_socket_store
    def _make_client():
        return socketio.test_client(app, flask_test_client=app.test_client())
    return _make_client
