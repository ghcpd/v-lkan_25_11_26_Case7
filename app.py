"""
Real-time Collaborative Document Editor
Flask-SocketIO backend with persistent storage and conflict detection
"""

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import json
import os
import time
from datetime import datetime
from collections import defaultdict
import uuid
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'collaborative-editor-secret-key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Data directories
DATA_DIR = 'data'
LOGS_DIR = os.path.join(DATA_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

class DocumentManager:
    """Manages document state, persistence, and edit logging"""
    
    def __init__(self):
        self.documents = {}  # doc_id -> {content, version, last_modified}
        self.active_users = defaultdict(set)  # doc_id -> set of user_ids
        self.recent_edits = defaultdict(list)  # doc_id -> list of recent edits
        self.load_documents()
    
    def load_documents(self):
        """Load all documents from JSONL logs on startup"""
        logger.info("Loading documents from persistent storage...")
        
        if not os.path.exists(LOGS_DIR):
            logger.info("No logs directory found, starting fresh")
            return
        
        for filename in os.listdir(LOGS_DIR):
            if filename.endswith('.jsonl'):
                doc_id = filename[:-6]  # Remove .jsonl extension
                self._rebuild_document(doc_id)
        
        logger.info(f"Loaded {len(self.documents)} documents")
    
    def _rebuild_document(self, doc_id):
        """Rebuild document state by replaying JSONL log"""
        log_path = os.path.join(LOGS_DIR, f"{doc_id}.jsonl")
        
        if not os.path.exists(log_path):
            return
        
        content = ""
        version = 0
        last_modified = None
        
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        if record.get('action') == 'edit':
                            content = record.get('content', '')
                            version = record.get('version', version)
                            last_modified = record.get('timestamp')
        except Exception as e:
            logger.error(f"Error rebuilding document {doc_id}: {e}")
            return
        
        self.documents[doc_id] = {
            'content': content,
            'version': version,
            'last_modified': last_modified or datetime.utcnow().isoformat()
        }
        
        logger.info(f"Rebuilt document {doc_id} with version {version}")
    
    def log_edit(self, doc_id, user_id, content, metadata=None):
        """Append edit to JSONL log file"""
        log_path = os.path.join(LOGS_DIR, f"{doc_id}.jsonl")
        
        version = self.documents[doc_id]['version'] + 1
        self.documents[doc_id]['version'] = version
        
        record = {
            'action': 'edit',
            'doc_id': doc_id,
            'user_id': user_id,
            'content': content,
            'version': version,
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': metadata or {}
        }
        
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record) + '\n')
        except Exception as e:
            logger.error(f"Error logging edit for {doc_id}: {e}")
        
        return version
    
    def create_document(self, doc_id=None):
        """Create a new document"""
        if doc_id is None:
            doc_id = str(uuid.uuid4())[:8]
        
        if doc_id in self.documents:
            return doc_id, self.documents[doc_id]
        
        self.documents[doc_id] = {
            'content': '',
            'version': 0,
            'last_modified': datetime.utcnow().isoformat()
        }
        
        # Create log file
        log_path = os.path.join(LOGS_DIR, f"{doc_id}.jsonl")
        with open(log_path, 'w', encoding='utf-8') as f:
            record = {
                'action': 'create',
                'doc_id': doc_id,
                'timestamp': datetime.utcnow().isoformat()
            }
            f.write(json.dumps(record) + '\n')
        
        logger.info(f"Created new document: {doc_id}")
        return doc_id, self.documents[doc_id]
    
    def get_document(self, doc_id):
        """Get document by ID, create if doesn't exist"""
        if doc_id not in self.documents:
            return self.create_document(doc_id)
        return doc_id, self.documents[doc_id]
    
    def update_document(self, doc_id, content, user_id, cursor_position=None):
        """Update document content with LWW strategy"""
        if doc_id not in self.documents:
            self.create_document(doc_id)
        
        old_content = self.documents[doc_id]['content']
        self.documents[doc_id]['content'] = content
        self.documents[doc_id]['last_modified'] = datetime.utcnow().isoformat()
        
        # Log the edit
        version = self.log_edit(doc_id, user_id, content, {
            'cursor_position': cursor_position
        })
        
        # Track recent edits for conflict detection
        edit_info = {
            'user_id': user_id,
            'timestamp': time.time(),
            'old_content': old_content,
            'new_content': content,
            'affected_lines': self._get_affected_lines(old_content, content)
        }
        
        self.recent_edits[doc_id].append(edit_info)
        
        # Keep only last 10 edits for conflict detection
        if len(self.recent_edits[doc_id]) > 10:
            self.recent_edits[doc_id] = self.recent_edits[doc_id][-10:]
        
        return version, edit_info
    
    def _get_affected_lines(self, old_content, new_content):
        """Determine which line ranges were affected by the edit"""
        old_lines = old_content.split('\n')
        new_lines = new_content.split('\n')
        
        # Simple diff: find first and last differing line
        first_diff = None
        last_diff = None
        
        max_len = max(len(old_lines), len(new_lines))
        
        for i in range(max_len):
            old_line = old_lines[i] if i < len(old_lines) else None
            new_line = new_lines[i] if i < len(new_lines) else None
            
            if old_line != new_line:
                if first_diff is None:
                    first_diff = i
                last_diff = i
        
        if first_diff is None:
            return []
        
        return list(range(first_diff, last_diff + 1))
    
    def detect_conflict(self, doc_id, current_edit):
        """Detect if current edit conflicts with recent edits"""
        if doc_id not in self.recent_edits:
            return None
        
        current_time = current_edit['timestamp']
        current_user = current_edit['user_id']
        current_lines = set(current_edit['affected_lines'])
        
        # Check edits within last 2 seconds from different users
        conflicts = []
        
        for edit in self.recent_edits[doc_id]:
            if edit['user_id'] == current_user:
                continue
            
            time_diff = current_time - edit['timestamp']
            if time_diff > 2.0:  # Only check recent edits
                continue
            
            edit_lines = set(edit['affected_lines'])
            
            # Check for overlapping or adjacent lines
            if current_lines & edit_lines or \
               any(abs(cl - el) <= 1 for cl in current_lines for el in edit_lines):
                conflicts.append({
                    'user_id': edit['user_id'],
                    'timestamp': edit['timestamp'],
                    'affected_lines': edit['affected_lines']
                })
        
        if conflicts:
            return {
                'detected': True,
                'current_user': current_user,
                'current_lines': list(current_lines),
                'conflicts': conflicts
            }
        
        return None
    
    def add_user(self, doc_id, user_id):
        """Add user to document's active users"""
        self.active_users[doc_id].add(user_id)
        return len(self.active_users[doc_id])
    
    def remove_user(self, doc_id, user_id):
        """Remove user from document's active users"""
        self.active_users[doc_id].discard(user_id)
        return len(self.active_users[doc_id])
    
    def get_user_count(self, doc_id):
        """Get number of active users for a document"""
        return len(self.active_users[doc_id])

# Global document manager instance
doc_manager = DocumentManager()

# Track user sessions
user_sessions = {}  # session_id -> {user_id, doc_id}

@app.route('/')
def index():
    """Render main page"""
    return render_template('index.html')

@app.route('/document/<doc_id>')
def document_view(doc_id):
    """Render document editor page"""
    return render_template('editor.html', doc_id=doc_id)

@app.route('/api/documents', methods=['POST'])
def create_document():
    """API endpoint to create a new document"""
    doc_id, doc_data = doc_manager.create_document()
    return jsonify({
        'doc_id': doc_id,
        'content': doc_data['content'],
        'version': doc_data['version']
    })

@app.route('/api/documents/<doc_id>', methods=['GET'])
def get_document(doc_id):
    """API endpoint to get document content"""
    doc_id, doc_data = doc_manager.get_document(doc_id)
    return jsonify({
        'doc_id': doc_id,
        'content': doc_data['content'],
        'version': doc_data['version'],
        'user_count': doc_manager.get_user_count(doc_id)
    })

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    session_id = request.sid
    user_id = f"user-{str(uuid.uuid4())[:6]}"
    
    user_sessions[session_id] = {
        'user_id': user_id,
        'doc_id': None
    }
    
    emit('user_assigned', {'user_id': user_id})
    logger.info(f"User connected: {user_id} (session: {session_id})")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    session_id = request.sid
    
    if session_id in user_sessions:
        user_data = user_sessions[session_id]
        user_id = user_data['user_id']
        doc_id = user_data['doc_id']
        
        if doc_id:
            leave_room(doc_id)
            user_count = doc_manager.remove_user(doc_id, user_id)
            
            emit('user_left', {
                'user_id': user_id,
                'user_count': user_count
            }, room=doc_id)
        
        del user_sessions[session_id]
        logger.info(f"User disconnected: {user_id}")

@socketio.on('join_document')
def handle_join_document(data):
    """Handle user joining a document"""
    session_id = request.sid
    doc_id = data.get('doc_id')
    
    if session_id not in user_sessions:
        return
    
    user_id = user_sessions[session_id]['user_id']
    
    # Leave previous document if any
    old_doc_id = user_sessions[session_id]['doc_id']
    if old_doc_id:
        leave_room(old_doc_id)
        doc_manager.remove_user(old_doc_id, user_id)
    
    # Join new document
    join_room(doc_id)
    user_sessions[session_id]['doc_id'] = doc_id
    
    # Get document data
    doc_id, doc_data = doc_manager.get_document(doc_id)
    user_count = doc_manager.add_user(doc_id, user_id)
    
    # Send document state to joining user
    emit('document_state', {
        'content': doc_data['content'],
        'version': doc_data['version'],
        'user_count': user_count
    })
    
    # Notify others
    emit('user_joined', {
        'user_id': user_id,
        'user_count': user_count
    }, room=doc_id, skip_sid=session_id)
    
    logger.info(f"User {user_id} joined document {doc_id}")

@socketio.on('edit_document')
def handle_edit_document(data):
    """Handle document edit from client"""
    session_id = request.sid
    
    if session_id not in user_sessions:
        return
    
    user_id = user_sessions[session_id]['user_id']
    doc_id = user_sessions[session_id]['doc_id']
    
    if not doc_id:
        return
    
    content = data.get('content', '')
    cursor_position = data.get('cursor_position')
    
    # Update document (LWW strategy)
    version, edit_info = doc_manager.update_document(
        doc_id, content, user_id, cursor_position
    )
    
    # Detect conflicts
    conflict_data = doc_manager.detect_conflict(doc_id, edit_info)
    
    # Broadcast update to all clients
    emit('document_updated', {
        'content': content,
        'version': version,
        'user_id': user_id,
        'timestamp': datetime.utcnow().isoformat()
    }, room=doc_id, skip_sid=session_id)
    
    # If conflict detected, broadcast conflict event
    if conflict_data:
        emit('conflict_detected', conflict_data, room=doc_id)
        logger.warning(f"Conflict detected in document {doc_id}: {conflict_data}")

@socketio.on('request_history')
def handle_request_history(data):
    """Send document edit history"""
    doc_id = data.get('doc_id')
    
    if not doc_id:
        return
    
    log_path = os.path.join(LOGS_DIR, f"{doc_id}.jsonl")
    
    if not os.path.exists(log_path):
        emit('history_response', {'history': []})
        return
    
    history = []
    
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    if record.get('action') == 'edit':
                        history.append({
                            'user_id': record.get('user_id'),
                            'version': record.get('version'),
                            'timestamp': record.get('timestamp'),
                            'preview': record.get('content', '')[:100]
                        })
    except Exception as e:
        logger.error(f"Error reading history for {doc_id}: {e}")
    
    emit('history_response', {'history': history})

if __name__ == '__main__':
    logger.info("Starting collaborative editor server...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
