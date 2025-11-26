import os
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple
from threading import Lock

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room

# Constants
LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
CONFLICT_WINDOW_SECONDS = 3  # If edits within 3 seconds overlap, flag as conflict

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = 'dev'
socketio = SocketIO(app, cors_allowed_origins='*')

# In-memory document store
DOCS: Dict[str, Dict] = {}
DOCS_LOCK = Lock()

# Presence: {doc_id: {sid: user_id}}
PRESENCE: Dict[str, Dict] = {}


# Utilities for JSONL persistence

def log_path(doc_id: str) -> Path:
    return LOG_DIR / f"{doc_id}.jsonl"


def append_log(doc_id: str, record: dict):
    p = log_path(doc_id)
    with open(p, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def replay_logs():
    """Load logs from disk and rebuild DOCS state."""
    for p in LOG_DIR.glob('*.jsonl'):
        doc_id = p.stem
        with open(p, 'r', encoding='utf-8') as f:
            content = ""
            version = 0
            edits = []
            for line in f:
                rec = json.loads(line)
                edits.append(rec)
                content = rec.get('content', content)
                version = rec.get('version', version)
            DOCS[doc_id] = {
                'content': content,
                'version': version,
                'last_updated': edits[-1]['timestamp'] if edits else time.time(),
                'edits': edits,
            }
            PRESENCE.setdefault(doc_id, {})


# Server startup: rebuild docs
replay_logs()


# Simple helper to compute line ranges for a text: returns (start_line, end_line) 0-based inclusive
def line_range_for_diff(old: str, new: str) -> Tuple[int, int]:
    if old == new:
        return (-1, -1)
    old_lines = old.splitlines()
    new_lines = new.splitlines()
    start = 0
    while start < len(old_lines) and start < len(new_lines) and old_lines[start] == new_lines[start]:
        start += 1
    end_old = len(old_lines) - 1
    end_new = len(new_lines) - 1
    while end_old >= start and end_new >= start and old_lines[end_old] == new_lines[end_new]:
        end_old -= 1
        end_new -= 1
    return (start, end_new if end_new >= start else start)


# Conflict detection

def detect_conflict(doc_id: str, new_edit: dict) -> List[dict]:
    """Returns list of conflicting edit records, if any"""
    conflicts = []
    edits = DOCS[doc_id]['edits'][-50:]  # look at last N edits
    for e in edits:
        dt = abs(new_edit['timestamp'] - e['timestamp'])
        if dt <= CONFLICT_WINDOW_SECONDS:
            # if line ranges overlap
            s1, e1 = new_edit['edited_lines'] if 'edited_lines' in new_edit else (-1, -1)
            s2, e2 = e.get('edited_lines', (-1, -1))
            if s1 == -1 or s2 == -1:
                continue
            if not (e1 < s2 or e2 < s1):
                conflicts.append(e)
    return conflicts


# API endpoints
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/docs', methods=['GET'])
def list_docs():
    """Return list of document IDs and basic info"""
    with DOCS_LOCK:
        return jsonify([{'doc_id': doc_id, 'version': d['version']} for doc_id, d in DOCS.items()])


@app.route('/docs', methods=['POST'])
def create_doc():
    req = request.get_json()
    doc_id = req.get('doc_id')
    if not doc_id:
        return jsonify({'error': 'doc_id required'}), 400
    with DOCS_LOCK:
        if doc_id in DOCS:
            return jsonify({'error': 'doc exists'}), 400
        DOCS[doc_id] = {'content': '', 'version': 0, 'last_updated': time.time(), 'edits': []}
        PRESENCE.setdefault(doc_id, {})
    return jsonify({'doc_id': doc_id}), 201


# SocketIO events
@socketio.on('join')
def on_join(data):
    doc_id = data.get('doc_id')
    user_id = data.get('user_id')
    sid = request.sid
    join_room(doc_id)
    # add to presence
    with DOCS_LOCK:
        PRESENCE.setdefault(doc_id, {})
        PRESENCE[doc_id][sid] = user_id
        if doc_id not in DOCS:
            DOCS[doc_id] = {'content': '', 'version': 0, 'last_updated': time.time(), 'edits': []}
    # send current content and presence
    emit('doc_state', {'doc_id': doc_id, 'content': DOCS[doc_id]['content'], 'version': DOCS[doc_id]['version']})
    socketio.emit('presence', {'count': len(PRESENCE[doc_id])}, room=doc_id)


@socketio.on('leave')
def on_leave(data):
    doc_id = data.get('doc_id')
    sid = request.sid
    leave_room(doc_id)
    with DOCS_LOCK:
        PRESENCE.get(doc_id, {}).pop(sid, None)
    socketio.emit('presence', {'count': len(PRESENCE.get(doc_id, {}))}, room=doc_id)


@socketio.on('edit')
def on_edit(data):
    doc_id = data.get('doc_id')
    content = data.get('content')
    user_id = data.get('user_id')
    edited_lines = tuple(data.get('edited_lines', (-1, -1)))
    # apply LWW: accept update as authoritative by arrival time
    with DOCS_LOCK:
        if doc_id not in DOCS:
            DOCS[doc_id] = {'content': '', 'version': 0, 'last_updated': time.time(), 'edits': []}
        doc = DOCS[doc_id]
        timestamp = time.time()
        version = doc['version'] + 1
        edit_record = {
            'timestamp': timestamp,
            'user_id': user_id,
            'doc_id': doc_id,
            'content': content,
            'edited_lines': edited_lines,
            'version': version,
        }
        # detect conflicts
        conflicts = detect_conflict(doc_id, edit_record) if doc['edits'] else []
        if conflicts:
            # broadcast conflict event
            socketio.emit('conflict', {'doc_id': doc_id, 'new_edit': edit_record, 'conflicts': conflicts}, room=doc_id)
        # persist
        append_log(doc_id, edit_record)
        # update in-memory
        doc['content'] = content
        doc['version'] = version
        doc['last_updated'] = timestamp
        doc['edits'].append(edit_record)
    # broadcast to room all clients
    socketio.emit('doc_update', {'doc_id': doc_id, 'content': content, 'version': version, 'timestamp': timestamp, 'user_id': user_id}, room=doc_id)


@socketio.on('get_history')
def on_get_history(data):
    doc_id = data.get('doc_id')
    with DOCS_LOCK:
        edits = DOCS.get(doc_id, {}).get('edits', [])
    emit('history', {'doc_id': doc_id, 'edits': edits[-100:]})


# On disconnect, update presence
@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    changed_docs = []
    with DOCS_LOCK:
        for doc_id, sockets in PRESENCE.items():
            if sid in sockets:
                sockets.pop(sid)
                changed_docs.append(doc_id)
    for doc_id in changed_docs:
        socketio.emit('presence', {'count': len(PRESENCE.get(doc_id, {}))}, room=doc_id)


if __name__ == '__main__':
    # using eventlet if available
    try:
        import eventlet
        eventlet.monkey_patch()
    except ImportError:
        pass
    socketio.run(app, host='0.0.0.0', port=5000)
