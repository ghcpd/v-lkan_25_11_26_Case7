import os
import json
import time
import uuid
from threading import Lock
from flask import Flask, send_from_directory, jsonify, request
from flask_socketio import SocketIO, join_room, leave_room

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, 'data')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

app = Flask(__name__, static_folder='static')
# Use the threading async mode for broad compatibility on Windows/different hosts.
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')


def short_user_id():
    return f"user-{uuid.uuid4().hex[:6]}"


class DocumentStore:
    def __init__(self):
        self.lock = Lock()
        self.docs = {}  # doc_id -> {'content': str, 'last_edit_times': {line_idx: ts}, 'presence': set()}
        self._load_all()

    def _log_path(self, doc_id):
        return os.path.join(LOGS_DIR, f"{doc_id}.jsonl")

    def _data_path(self, doc_id):
        return os.path.join(DATA_DIR, f"{doc_id}.txt")

    def _load_all(self):
        # Rebuild docs by replaying jsonl logs
        for name in os.listdir(LOGS_DIR):
            if not name.endswith('.jsonl'):
                continue
            doc_id = name[:-6]
            self.rebuild_from_log(doc_id)

    def rebuild_from_log(self, doc_id):
        path = self._log_path(doc_id)
        if not os.path.exists(path):
            return
        content = ''
        last_edit_times = {}
        with open(path, 'r', encoding='utf-8') as fh:
            for raw in fh:
                try:
                    rec = json.loads(raw)
                except Exception:
                    continue
                if 'content' in rec:
                    content = rec['content']
                    ts = rec.get('ts', time.time())
                    lines = rec.get('lines', [])
                    for l in lines:
                        last_edit_times[l] = ts
        # persist reconstructed content for quick load
        with open(self._data_path(doc_id), 'w', encoding='utf-8') as fh:
            fh.write(content)
        self.docs[doc_id] = {'content': content, 'last_edit_times': last_edit_times, 'presence': set()}

    def create(self, doc_id):
        with self.lock:
            if doc_id in self.docs:
                return self.docs[doc_id]
            self.docs[doc_id] = {'content': '', 'last_edit_times': {}, 'presence': set()}
            self._persist_content(doc_id)
            return self.docs[doc_id]

    def _persist_content(self, doc_id):
        p = self._data_path(doc_id)
        with open(p, 'w', encoding='utf-8') as fh:
            fh.write(self.docs[doc_id]['content'])

    def append_log(self, doc_id, rec):
        path = self._log_path(doc_id)
        with open(path, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + '\n')

    def get(self, doc_id):
        with self.lock:
            if doc_id not in self.docs:
                self.create(doc_id)
            return self.docs[doc_id]

    def apply_update(self, doc_id, content, user_id, ts=None, lines=None):
        ts = ts or time.time()
        with self.lock:
            doc = self.get(doc_id)
            # LWW: accept the incoming content as authoritative
            prev_content = doc['content']
            doc['content'] = content
            # update last_edit_times for provided lines
            if isinstance(lines, list):
                for l in lines:
                    doc['last_edit_times'][l] = ts
            # persist change and append to log
            self._persist_content(doc_id)
            rec = {'ts': ts, 'user': user_id, 'content': content, 'lines': lines or []}
            self.append_log(doc_id, rec)
            return prev_content, rec

    def set_presence(self, doc_id, session_id, present=True):
        with self.lock:
            doc = self.get(doc_id)
            if present:
                doc['presence'].add(session_id)
            else:
                doc['presence'].discard(session_id)
            return len(doc['presence'])


store = DocumentStore()
# session mapping: sid -> user_id
sid_to_user = {}


@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/doc/<doc_id>', methods=['GET'])
def get_doc(doc_id):
    doc = store.get(doc_id)
    return jsonify({'doc_id': doc_id, 'content': doc['content'], 'presence': len(doc['presence'])})


@app.route('/logs/<doc_id>', methods=['GET'])
def get_logs(doc_id):
    path = store._log_path(doc_id)
    if not os.path.exists(path):
        return jsonify({'logs': []})
    out = []
    with open(path, 'r', encoding='utf-8') as fh:
        for raw in fh:
            try:
                out.append(json.loads(raw))
            except Exception:
                continue
    return jsonify({'logs': out})


@socketio.on('connect')
def on_connect():
    sid = request.sid
    user_id = short_user_id()
    # attach session user id for this connection
    sid_to_user[sid] = user_id
    print(f"[socket] connect sid={sid} user={user_id}")
    socketio.emit('session', {'session_id': sid, 'user_id': user_id}, room=sid)


@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    # remove this sid from any document presence lists and notify rooms
    for doc_id, info in list(store.docs.items()):
        if sid in info['presence']:
            presence = store.set_presence(doc_id, sid, present=False)
            socketio.emit('presence', {'doc_id': doc_id, 'presence': presence}, room=doc_id)
    # drop mapping
    sid_to_user.pop(sid, None)


@socketio.on('join')
def on_join(data):
    doc_id = data.get('doc_id')
    if not doc_id:
        return
    sid = request.sid
    join_room(doc_id)
    print(f"[socket] {sid} JOIN doc={doc_id}")
    presence = store.set_presence(doc_id, sid, present=True)
    doc = store.get(doc_id)
    # send current content and presence count
    socketio.emit('document', {'doc_id': doc_id, 'content': doc['content'], 'presence': presence}, room=sid)
    # notify room of presence change
    socketio.emit('presence', {'doc_id': doc_id, 'presence': presence}, room=doc_id)


@socketio.on('leave')
def on_leave(data):
    doc_id = data.get('doc_id')
    sid = request.sid
    leave_room(doc_id)
    print(f"[socket] {sid} LEAVE doc={doc_id}")
    presence = store.set_presence(doc_id, sid, present=False)
    socketio.emit('presence', {'doc_id': doc_id, 'presence': presence}, room=doc_id)


def detect_conflict(doc, incoming_lines, incoming_ts, incoming_user):
    # A conflict occurs if any incoming line index was edited by another user
    # within a short window (e.g., 2 seconds), or adjacent lines were edited.
    window = 2.0
    conflicts = []
    for l in incoming_lines or []:
        last_ts = doc['last_edit_times'].get(l)
        if last_ts and (incoming_ts - last_ts) <= window:
            conflicts.append(l)
        # check adjacent
        last_ts_lm1 = doc['last_edit_times'].get(l-1)
        last_ts_lp1 = doc['last_edit_times'].get(l+1)
        if last_ts_lm1 and (incoming_ts - last_ts_lm1) <= window:
            conflicts.append(l-1)
        if last_ts_lp1 and (incoming_ts - last_ts_lp1) <= window:
            conflicts.append(l+1)
    return sorted(set(conflicts))


@socketio.on('update')
def on_update(data):
    # data must include: doc_id, content, ts(optional), user_id, lines(optional array of indices)
    doc_id = data.get('doc_id')
    content = data.get('content')
    ts = data.get('ts', time.time())
    user_id = data.get('user_id') or sid_to_user.get(request.sid, 'anon')
    lines = data.get('lines') or []
    if not doc_id or content is None:
        return

    doc = store.get(doc_id)

    # detect conflicts
    conflicts = detect_conflict(doc, lines, ts, user_id)
    print(f"[socket] update doc={doc_id} user={user_id} ts={ts} lines={lines}")
    if conflicts:
        # broadcast conflict notification (simulation only)
        socketio.emit('conflict', {'doc_id': doc_id, 'conflicts': conflicts, 'user': user_id}, room=doc_id)
        # also write a conflict record to the log for diagnostic purposes
        conflict_rec = {'ts': ts, 'type': 'conflict', 'user': user_id, 'conflicts': conflicts}
        store.append_log(doc_id, conflict_rec)

    prev_content, rec = store.apply_update(doc_id, content, user_id, ts=ts, lines=lines)
    print(f"[store] apply update doc={doc_id} user={user_id} prev_len={len(prev_content)} new_len={len(content)}")
    # After LWW applies, broadcast updated authoritative content
    socketio.emit('document', {'doc_id': doc_id, 'content': content, 'presence': len(doc['presence'])}, room=doc_id)


if __name__ == '__main__':
    print('Starting server on http://127.0.0.1:5000 (bound to localhost for local testing)')
    # bind to localhost for local testing (avoids using 0.0.0.0 which some browsers show as invalid)
    socketio.run(app, host='127.0.0.1', port=5000)
