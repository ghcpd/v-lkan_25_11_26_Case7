import os
import time
import json
import tempfile
import shutil
from collab_app import app, socketio
from collab_app.collaboration import manager, LOGS_DIR
from flask_socketio import SocketIOTestClient

# use the socketio test client

def make_client():
    return socketio.test_client(app, flask_test_client=app.test_client())


def setup_function(function):
    # Clear any existing docs and logs for test isolation
    for d in list(manager.docs.keys()):
        manager.docs.pop(d, None)
    manager.presence.clear()
    for fname in os.listdir(LOGS_DIR):
        if fname.endswith('.jsonl'):
            os.unlink(os.path.join(LOGS_DIR, fname))


def test_create_and_presence(tmp_path):
    # ensure logs dir is empty for test
    # override LOGS_DIR not easy; we'll just ensure manager has been loaded
    c1 = make_client()
    c2 = make_client()
    assert c1.is_connected()
    # get user ids from welcome
    welcome1 = c1.get_received()
    welcome2 = c2.get_received()
    user1 = None
    user2 = None
    for e in welcome1:
        if e['name'] == 'welcome':
            user1 = e['args'][0]['user_id']
    for e in welcome2:
        if e['name'] == 'welcome':
            user2 = e['args'][0]['user_id']
    assert user1 and user2
    # create doc from client 1
    doc_id = 'testdoc'
    c1.emit('create_doc', {'doc_id': doc_id, 'content': 'Hello\n', 'user_id': user1})
    time.sleep(0.1)
    # both join
    c1.emit('join_doc', {'doc_id': doc_id, 'user_id': user1})
    c2.emit('join_doc', {'doc_id': doc_id, 'user_id': user2})
    time.sleep(0.1)
    # check presence update events
    ev1 = c1.get_received()
    ev2 = c2.get_received()
    # verify presence count 2
    found=False
    for e in ev1+ev2:
        if e['name']=='presence_update' and e['args'][0]['count']==2:
            found=True
    assert found


def test_edit_and_persistence(tmp_path):
    # clear current doc logs
    doc_id = 'testdoc'
    path = os.path.join(LOGS_DIR, f"{doc_id}.jsonl")
    if os.path.exists(path):
        os.unlink(path)
    c1 = make_client()
    c2 = make_client()
    user1 = None
    user2 = None
    for e in c1.get_received():
        if e['name']=='welcome': user1 = e['args'][0]['user_id']
    for e in c2.get_received():
        if e['name']=='welcome': user2 = e['args'][0]['user_id']
    c1.emit('create_doc', {'doc_id': doc_id, 'content': 'Line1\n', 'user_id': user1})
    time.sleep(0.1)
    c1.emit('join_doc', {'doc_id': doc_id, 'user_id': user1})
    c2.emit('join_doc', {'doc_id': doc_id, 'user_id': user2})
    time.sleep(0.1)
    c1.emit('edit', {'doc_id': doc_id, 'content': 'Line1\nLine2\n', 'user_id': user1, 'ts': time.time(), 'start_line': 2, 'end_line': 2})
    time.sleep(0.2)
    # client 2 should get update
    ev = c2.get_received()
    updates = [e for e in ev if e['name']=='doc_update']
    assert updates and updates[-1]['args'][0]['content'].endswith('Line2\n')
    # check persistence file contains at least two entries
    with open(path, 'r', encoding='utf-8') as fh:
        lines = fh.read().strip().split('\n')
    assert len(lines) >= 2


def test_conflict_detection(tmp_path):
    doc_id = 'testconf'
    path = os.path.join(LOGS_DIR, f"{doc_id}.jsonl")
    if os.path.exists(path): os.unlink(path)
    c1 = make_client(); c2 = make_client()
    user1 = None; user2 = None
    for e in c1.get_received():
        if e['name']=='welcome': user1 = e['args'][0]['user_id']
    for e in c2.get_received():
        if e['name']=='welcome': user2 = e['args'][0]['user_id']
    c1.emit('create_doc', {'doc_id': doc_id, 'content': 'A\nB\nC\n', 'user_id': user1})
    c1.emit('join_doc', {'doc_id': doc_id, 'user_id': user1})
    c2.emit('join_doc', {'doc_id': doc_id, 'user_id': user2})
    time.sleep(0.1)
    ts = time.time()
    c1.emit('edit', {'doc_id': doc_id, 'content': 'X\nB\nC\n', 'user_id': user1, 'ts': ts, 'start_line': 1, 'end_line': 1})
    # second client edits same line within window
    c2.emit('edit', {'doc_id': doc_id, 'content': 'Y\nB\nC\n', 'user_id': user2, 'ts': ts+0.5, 'start_line': 1, 'end_line': 1})
    time.sleep(0.1)
    # both clients should receive conflict event
    ev1 = c1.get_received(); ev2 = c2.get_received()
    conflicts1 = [e for e in ev1 if e['name']=='conflict']
    conflicts2 = [e for e in ev2 if e['name']=='conflict']
    assert conflicts1 and conflicts2


def test_lww_resolution(tmp_path):
    doc_id = 'testlww'
    path = os.path.join(LOGS_DIR, f"{doc_id}.jsonl")
    if os.path.exists(path): os.unlink(path)
    c1 = make_client(); c2 = make_client()
    user1 = None; user2 = None
    for e in c1.get_received():
        if e['name']=='welcome': user1 = e['args'][0]['user_id']
    for e in c2.get_received():
        if e['name']=='welcome': user2 = e['args'][0]['user_id']
    c1.emit('create_doc', {'doc_id': doc_id, 'content': 'Original\n', 'user_id': user1})
    c1.emit('join_doc', {'doc_id': doc_id, 'user_id': user1})
    c2.emit('join_doc', {'doc_id': doc_id, 'user_id': user2})
    time.sleep(0.1)
    t0 = time.time()
    c1.emit('edit', {'doc_id': doc_id, 'content': 'A\n', 'user_id': user1, 'ts': t0, 'start_line': 1, 'end_line': 1})
    # second edit later
    c2.emit('edit', {'doc_id': doc_id, 'content': 'B\n', 'user_id': user2, 'ts': t0 + 1, 'start_line': 1, 'end_line': 1})
    time.sleep(0.1)
    # the document should be the last edit (B)
    doc = manager.get_doc(doc_id)
    assert doc.content.strip() == 'B'


def test_multi_document_isolation(tmp_path):
    doc1 = 'docA'; doc2 = 'docB'
    c1 = make_client(); c2 = make_client(); c3 = make_client()
    u1 = None; u2 = None; u3 = None
    for e in c1.get_received():
        if e['name']=='welcome': u1 = e['args'][0]['user_id']
    for e in c2.get_received():
        if e['name']=='welcome': u2 = e['args'][0]['user_id']
    for e in c3.get_received():
        if e['name']=='welcome': u3 = e['args'][0]['user_id']
    c1.emit('create_doc', {'doc_id': doc1, 'content': '1\n', 'user_id': u1})
    c2.emit('create_doc', {'doc_id': doc2, 'content': 'A\n', 'user_id': u2})
    time.sleep(0.1)
    c1.emit('join_doc', {'doc_id': doc1, 'user_id': u1})
    c3.emit('join_doc', {'doc_id': doc2, 'user_id': u3})
    time.sleep(0.1)
    c1.emit('edit', {'doc_id': doc1, 'content': '1\n2\n', 'user_id': u1, 'ts': time.time(), 'start_line':2, 'end_line':2})
    c3.emit('edit', {'doc_id': doc2, 'content': 'A\nB\n', 'user_id': u3, 'ts': time.time(), 'start_line':2, 'end_line':2})
    time.sleep(0.2)
    d1 = manager.get_doc(doc1).content
    d2 = manager.get_doc(doc2).content
    assert '2' in d1 and 'B' in d2

