import os
import sys

# Ensure the project root is on sys.path so tests can import app (works when pytest is executed from tests/)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import time
import subprocess
import signal
import requests
import json
import socketio

from app import store, detect_conflict


def test_persistence_and_replay(tmp_path):
    doc = 'test_persist_' + str(int(time.time()*1000))
    content1 = 'line1\nline2\n'
    user = 'test-user'
    ts = time.time()
    # apply update
    store.apply_update(doc, content1, user, ts=ts, lines=[0,1])
    # check logs exist
    logs_path = os.path.join(os.path.dirname(__file__), '..', 'logs', f'{doc}.jsonl')
    assert os.path.exists(logs_path)
    # rebuild with a fresh store instance
    new_store = type(store)()
    new_store.rebuild_from_log(doc)
    d = new_store.get(doc)
    assert d['content'] == content1


def test_conflict_detection_logic():
    doc_id = 'test_conflict_demo'
    # setup doc with an edit at line 1
    content = 'a\nb\nc\n'
    store.create(doc_id)
    store.apply_update(doc_id, content, 'u1', ts=1.0, lines=[1])
    # incoming edit at nearby line within window
    conflicts = detect_conflict(store.get(doc_id), [1], incoming_ts=1.5, incoming_user='u2')
    assert 1 in conflicts


def test_realtime_document_update_roundtrip_app_test_client():
    # Use Flask-SocketIO test_client to simulate two clients *in-process* without a network server.
    from app import socketio as server_socketio, app as flask_app

    # create two test clients connected to the same app
    client_a = server_socketio.test_client(flask_app, namespace='/')
    client_b = server_socketio.test_client(flask_app, namespace='/')

    doc = 'test_rt_' + str(int(time.time() * 1000))

    # both clients join the same document room
    client_a.emit('join', {'doc_id': doc})
    client_b.emit('join', {'doc_id': doc})

    # client_b will collect received 'document' events
    received = []

    def on_doc(payload):
        received.append(payload)

    client_b.on('document', on_doc)

    # send update from client_a
    content = 'hello\nworld\n'
    payload = {'doc_id': doc, 'content': content, 'ts': time.time(), 'user_id': 'rt1', 'lines': [0, 1]}
    client_a.emit('update', payload)

    # give a short moment for the in-process event loop to dispatch
    time.sleep(0.1)

    # client_b should have received at least 1 document event with the updated content
    assert any((p.get('content') == content and p.get('doc_id') == doc) for p in received), (
        'client_b did not receive the update from client_a via in-process test_client')



def test_multi_document_isolation():
    d1 = 'isodoc1'
    d2 = 'isodoc2'
    store.create(d1)
    store.create(d2)
    store.apply_update(d1, 'a\nb\n', 'u1', ts=time.time(), lines=[0,1])
    store.apply_update(d2, 'x\ny\n', 'u2', ts=time.time(), lines=[0,1])
    assert store.get(d1)['content'].startswith('a')
    assert store.get(d2)['content'].startswith('x')
