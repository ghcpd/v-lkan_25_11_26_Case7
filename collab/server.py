import os
import time
import uuid
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
from .store import DocumentStore


def generate_user_id():
    return f"user-{uuid.uuid4().hex[:6]}"


def generate_doc_id():
    return f"doc-{uuid.uuid4().hex[:8]}"


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')


def create_app(testing: bool = False, data_dir: str = None):
    app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')
    app.config['TESTING'] = testing
    socketio = SocketIO(app, cors_allowed_origins="*", json=None)

    store = DocumentStore(data_dir=data_dir or os.environ.get('DATA_DIR', 'data'))
    store.load_all()

    # presence tracking: doc_id -> set(user_id); sid -> {user_id, doc_id}
    doc_presence = {}
    sid_map = {}

    @app.route('/')
    def index():
        docs = store.list_documents()
        return render_template('index.html', docs=docs)

    @app.route('/documents', methods=['POST'])
    def create_document():
        payload = request.get_json(silent=True) or {}
        doc_id = payload.get('doc_id') or generate_doc_id()
        store.get_or_create(doc_id)
        return jsonify({'doc_id': doc_id}), 201

    @app.route('/doc/<doc_id>')
    def document_page(doc_id):
        content, version = store.get_content(doc_id)
        return render_template('doc.html', doc_id=doc_id, content=content, version=version)

    @app.route('/api/documents/<doc_id>', methods=['GET'])
    def get_document(doc_id):
        content, version = store.get_content(doc_id)
        return jsonify({'doc_id': doc_id, 'content': content, 'version': version})

    @socketio.on('connect')
    def on_connect():
        user_id = generate_user_id()
        sid_map[request.sid] = {'user_id': user_id, 'doc_id': None}
        emit('user_assigned', {'user_id': user_id})

    @socketio.on('join_document')
    def on_join(data):
        doc_id = data.get('doc_id')
        if not doc_id:
            return
        join_room(doc_id)
        # update presence
        info = sid_map.get(request.sid)
        if info:
            info['doc_id'] = doc_id
            user_id = info['user_id']
        else:
            user_id = generate_user_id()
            sid_map[request.sid] = {'user_id': user_id, 'doc_id': doc_id}
        doc_presence.setdefault(doc_id, set()).add(user_id)

        content, version = store.get_content(doc_id)
        emit('document_state', {'doc_id': doc_id, 'content': content, 'version': version}, room=request.sid)
        emit('presence', {'doc_id': doc_id, 'count': len(doc_presence.get(doc_id, []))}, room=doc_id)

    @socketio.on('leave_document')
    def on_leave(data):
        doc_id = data.get('doc_id')
        info = sid_map.get(request.sid)
        if not doc_id or not info:
            return
        leave_room(doc_id)
        user_id = info.get('user_id')
        info['doc_id'] = None
        if doc_id in doc_presence and user_id in doc_presence[doc_id]:
            doc_presence[doc_id].remove(user_id)
            emit('presence', {'doc_id': doc_id, 'count': len(doc_presence.get(doc_id, []))}, room=doc_id)

    @socketio.on('edit_document')
    def on_edit(data):
        doc_id = data.get('doc_id')
        new_content = data.get('content')
        if doc_id is None or new_content is None:
            return
        info = sid_map.get(request.sid) or {}
        user_id = info.get('user_id') or generate_user_id()
        timestamp = time.time()
        version, changed_lines, conflict_info = store.apply_edit(doc_id, user_id, new_content, timestamp=timestamp)

        # broadcast updated state
        emit('document_updated', {
            'doc_id': doc_id,
            'content': new_content,
            'version': version,
            'user_id': user_id,
            'changed_lines': changed_lines,
            'timestamp': timestamp,
        }, room=doc_id)

        # presence broadcast (ensure counts correct if new doc)
        emit('presence', {'doc_id': doc_id, 'count': len(doc_presence.get(doc_id, []))}, room=doc_id)

        # conflict broadcast
        if conflict_info.get('has_conflict'):
            emit('conflict', {
                'doc_id': doc_id,
                'user_id': user_id,
                'lines': conflict_info.get('lines', []),
                'conflicts': conflict_info.get('conflicts', []),
                'timestamp': timestamp,
            }, room=doc_id)

    @socketio.on('disconnect')
    def on_disconnect():
        info = sid_map.pop(request.sid, None)
        if not info:
            return
        doc_id = info.get('doc_id')
        user_id = info.get('user_id')
        if doc_id and doc_id in doc_presence and user_id in doc_presence[doc_id]:
            doc_presence[doc_id].remove(user_id)
            emit('presence', {'doc_id': doc_id, 'count': len(doc_presence.get(doc_id, []))}, room=doc_id)

    return app, socketio, store


if __name__ == '__main__':
    app, socketio, _ = create_app()
    # optional: use eventlet if available
    try:
        import eventlet
        eventlet.monkey_patch()
        socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
    except ImportError:
        socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
