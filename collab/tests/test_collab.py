import os
import time
import json
from pathlib import Path
import pytest

# Make sure package root is on path when running tests from a nested folder
import sys, os
# Add the repository root (one level above `collab/`) to sys.path so `import collab` works
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))
from collab import server as collab

LOG_DIR = Path(collab.LOG_DIR)


@pytest.fixture(autouse=True)
def cleanup_logs(tmp_path, monkeypatch):
    # Make a temporary logs dir for each test
    new_logs = tmp_path / 'logs'
    new_logs.mkdir()
    monkeypatch.setattr(collab, 'LOG_DIR', new_logs)
    # ensure the in-memory structures are reset
    with collab.DOCS_LOCK:
        collab.DOCS.clear(); collab.PRESENCE.clear()
    yield


def test_join_and_presence():
    client_a = collab.socketio.test_client(collab.app)
    client_b = collab.socketio.test_client(collab.app)
    doc_id = 'doc-test'
    client_a.emit('join', {'doc_id': doc_id, 'user_id': 'a1'})
    received = client_a.get_received()
    # expect doc_state and presence
    assert any(x['name']=='doc_state' for x in received)
    assert any(x['name']=='presence' for x in received)
    client_b.emit('join', {'doc_id': doc_id, 'user_id': 'b2'})
    time.sleep(0.01)
    # presence should be broadcast: both clients have presence 2
    rA = client_a.get_received()
    rB = client_b.get_received()
    assert any(x['name']=='presence' and x['args'][0]['count']==2 for x in rA)
    assert any(x['name']=='presence' and x['args'][0]['count']==2 for x in rB)
    client_a.disconnect(); client_b.disconnect()


def test_edit_broadcast_and_persistence():
    client_a = collab.socketio.test_client(collab.app)
    client_b = collab.socketio.test_client(collab.app)
    doc_id = 'doc-edit'
    client_a.emit('join', {'doc_id': doc_id, 'user_id': 'a1'})
    client_b.emit('join', {'doc_id': doc_id, 'user_id': 'b2'})
    content1 = 'Line1\nLine2'
    client_a.emit('edit', {'doc_id': doc_id, 'content': content1, 'user_id': 'a1', 'edited_lines': [0,1]})
    time.sleep(0.05)
    # client_b should receive doc_update
    rec = client_b.get_received()
    assert any(m['name']=='doc_update' and m['args'][0]['content']==content1 for m in rec)
    # check log written
    log_file = collab.log_path(doc_id)
    assert log_file.exists()
    lines = list(open(log_file).read().strip().splitlines())
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data['content'] == content1
    client_a.disconnect(); client_b.disconnect()


def test_conflict_detection():
    client_a = collab.socketio.test_client(collab.app)
    client_b = collab.socketio.test_client(collab.app)
    doc = 'doc-conflict'
    client_a.emit('join', {'doc_id': doc, 'user_id': 'alice'})
    client_b.emit('join', {'doc_id': doc, 'user_id': 'bob'})
    base = 'A\nB\nC\nD'
    client_a.emit('edit', {'doc_id': doc, 'content': base, 'user_id': 'alice', 'edited_lines': [0,3]})
    time.sleep(0.01)
    # Two edits overlapping: alice changes line 1, bob changes line 2 within short window
    edit_a = 'A-1\nB\nC\nD'
    edit_b = 'A\nB-2\nC\nD'
    client_a.emit('edit', {'doc_id': doc, 'content': edit_a, 'user_id': 'alice', 'edited_lines': [0,0]})
    client_b.emit('edit', {'doc_id': doc, 'content': edit_b, 'user_id': 'bob', 'edited_lines': [1,1]})
    time.sleep(0.02)
    # Both should receive conflict event
    rec_a = client_a.get_received()
    rec_b = client_b.get_received()
    assert any(m['name']=='conflict' for m in rec_a)
    assert any(m['name']=='conflict' for m in rec_b)
    client_a.disconnect(); client_b.disconnect()


def test_get_history():
    client = collab.socketio.test_client(collab.app)
    doc = 'doc-hist'
    client.emit('join', {'doc_id': doc, 'user_id': 'u1'})
    client.emit('edit', {'doc_id': doc, 'content': 'Hello', 'user_id': 'u1', 'edited_lines': [0,0]})
    client.emit('edit', {'doc_id': doc, 'content': 'Hello\nWorld', 'user_id': 'u1', 'edited_lines': [1,1]})
    time.sleep(0.01)
    client.emit('get_history', {'doc_id': doc})
    rec = client.get_received()
    hist = [x for x in rec if x['name']=='history']
    assert hist and len(hist[0]['args'][0]['edits']) == 2
    client.disconnect()


def test_replay_logs():
    # Ensure that logs persisted are replayed on startup
    doc = 'doc-replay'
    # construct a fake log file
    recs = [
        {'timestamp': time.time()-10, 'user_id': 'u1', 'doc_id': doc, 'content': 'Line1', 'edited_lines': [0,0], 'version': 1},
        {'timestamp': time.time()-5, 'user_id': 'u2', 'doc_id': doc, 'content': 'Line1\nLine2', 'edited_lines': [1,1], 'version': 2},
    ]
    log_file = collab.log_path(doc)
    with open(log_file, 'w', encoding='utf-8') as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")
    # replay logs into memory
    collab.replay_logs()
    assert doc in collab.DOCS
    assert collab.DOCS[doc]['content'] == 'Line1\nLine2'
    assert collab.DOCS[doc]['version'] == 2
