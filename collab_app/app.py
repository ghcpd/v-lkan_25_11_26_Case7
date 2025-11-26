import os
import json
import time
import random
import string
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from .collaboration import manager

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='eventlet')

# Helpers

def random_user_id():
    return 'user-' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/docs')
def docs():
    return jsonify({'docs': manager.list_docs()})

@app.route('/docs/<doc_id>')
def get_doc(doc_id):
    doc = manager.get_doc(doc_id)
    if not doc:
        return jsonify({'error': 'not found'}), 404
    return jsonify({'doc_id': doc_id, 'content': doc.content, 'history': doc.edits})

@socketio.on('connect')
def handle_connect():
    user_id = random_user_id()
    # store user id in socket session
    request.sid_user_id = user_id
    manager.user_sessions[request.sid] = user_id
    emit('welcome', {'user_id': user_id})

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    user_id = manager.user_sessions.get(sid)
    # remove presence
    for doc_id in list(manager.presence.keys()):
        if user_id in manager.presence.get(doc_id, set()):
            manager.remove_presence(doc_id, user_id)
            socketio.emit('presence_update', {'doc_id': doc_id, 'count': manager.get_presence_count(doc_id)}, room=doc_id)
    if sid in manager.user_sessions:
        del manager.user_sessions[sid]

@socketio.on('join_doc')
def on_join(data):
    doc_id = data.get('doc_id')
    user_id = data.get('user_id')
    if not user_id:
        user_id = manager.user_sessions.get(request.sid)
    join_room(doc_id)
    manager.add_presence(doc_id, user_id)
    doc = manager.get_doc(doc_id)
    if not doc:
        emit('error', {'message': 'doc not found'})
        return
    emit('doc_state', {'doc_id': doc_id, 'content': doc.content})
    socketio.emit('presence_update', {'doc_id': doc_id, 'count': manager.get_presence_count(doc_id)}, room=doc_id)

@socketio.on('leave_doc')
def on_leave(data):
    doc_id = data.get('doc_id')
    user_id = data.get('user_id') or manager.user_sessions.get(request.sid)
    leave_room(doc_id)
    manager.remove_presence(doc_id, user_id)
    socketio.emit('presence_update', {'doc_id': doc_id, 'count': manager.get_presence_count(doc_id)}, room=doc_id)

@socketio.on('create_doc')
def on_create(data):
    doc_id = data.get('doc_id')
    content = data.get('content', '')
    user_id = data.get('user_id') or manager.user_sessions.get(request.sid)
    ok = manager.create_doc(doc_id, content, user_id)
    if not ok:
        emit('error', {'message': 'doc exists'})
        return
    socketio.emit('doc_created', {'doc_id': doc_id})

@socketio.on('edit')
def on_edit(data):
    doc_id = data.get('doc_id')
    content = data.get('content')
    user_id = data.get('user_id') or manager.user_sessions.get(request.sid)
    ts = data.get('ts') or time.time()
    start_line = data.get('start_line')
    end_line = data.get('end_line')

    # Apply edit (LWW)
    rec = manager.apply_edit(doc_id, content, user_id, ts, start_line=start_line, end_line=end_line)
    if not rec:
        emit('error', {'message': 'doc not found'})
        return
    # Broadcast update to room
    socketio.emit('doc_update', {'doc_id': doc_id, 'content': content, 'user_id': user_id, 'ts': ts}, room=doc_id)

    # Conflict detection
    is_conflict, conflicts = manager.detect_conflict(doc_id, user_id, ts, start_line, end_line)
    if is_conflict:
        socketio.emit('conflict', {'doc_id': doc_id, 'conflicts': conflicts}, room=doc_id)

@socketio.on('request_history')
def on_request_history(data):
    doc_id = data.get('doc_id')
    doc = manager.get_doc(doc_id)
    if not doc:
        emit('error', {'message': 'doc not found'})
        return
    emit('history', {'doc_id': doc_id, 'history': doc.edits})

if __name__ == '__main__':
    print('Starting collaborative server...')
    socketio.run(app, host='0.0.0.0', port=5000)
