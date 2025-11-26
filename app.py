"""
Lightweight Collaboration Platform with Real-time Editing, Presence Awareness, and Conflict Detection.

Features:
- Real-time collaborative editing via WebSockets
- Anonymous user sessions with temporary IDs
- Last-Write-Wins (LWW) conflict resolution
- Persistent edit logging (JSONL format)
- Conflict visualization with timestamp-based detection
- User presence tracking
"""

import os
import json
import uuid
import time
import logging
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from threading import Lock

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms

# ============================================================================
# Configuration & Logging
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'lightweight-collab-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Directories for persistence
DATA_DIR = Path(__file__).parent / 'data'
DATA_DIR.mkdir(exist_ok=True)
DOCUMENTS_DIR = DATA_DIR / 'documents'
DOCUMENTS_DIR.mkdir(exist_ok=True)
LOGS_DIR = DATA_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# ============================================================================
# Data Structures & State Management
# ============================================================================

class Document:
    """Represents a collaborative document with version history."""
    
    def __init__(self, doc_id, content='', version=0):
        self.id = doc_id
        self.content = content
        self.version = version
        self.lock = Lock()
        self.last_edit_time = time.time()
        self.edit_history = []  # For conflict tracking
    
    def update(self, new_content, user_id, edit_id, timestamp):
        """Update document content with Last-Write-Wins strategy."""
        with self.lock:
            self.content = new_content
            self.version += 1
            self.last_edit_time = timestamp
            self.edit_history.append({
                'user_id': user_id,
                'edit_id': edit_id,
                'timestamp': timestamp,
                'version': self.version
            })
    
    def to_dict(self):
        """Serialize document to dictionary."""
        return {
            'id': self.id,
            'content': self.content,
            'version': self.version,
            'last_edit_time': self.last_edit_time,
            'edit_count': len(self.edit_history)
        }


class DocumentManager:
    """Manages all documents and their persistence."""
    
    def __init__(self):
        self.documents = {}
        self.lock = Lock()
        self._load_all_documents()
    
    def get_or_create(self, doc_id):
        """Get existing document or create new one."""
        with self.lock:
            if doc_id not in self.documents:
                # Try to load from disk
                doc_path = DOCUMENTS_DIR / f'{doc_id}.json'
                if doc_path.exists():
                    with open(doc_path, 'r') as f:
                        data = json.load(f)
                        doc = Document(
                            doc_id,
                            content=data.get('content', ''),
                            version=data.get('version', 0)
                        )
                else:
                    doc = Document(doc_id)
                self.documents[doc_id] = doc
            return self.documents[doc_id]
    
    def save_document(self, doc_id):
        """Persist document to disk."""
        with self.lock:
            if doc_id in self.documents:
                doc = self.documents[doc_id]
                doc_path = DOCUMENTS_DIR / f'{doc_id}.json'
                with open(doc_path, 'w') as f:
                    json.dump({
                        'id': doc.id,
                        'content': doc.content,
                        'version': doc.version,
                        'last_edit_time': doc.last_edit_time
                    }, f, indent=2)
    
    def _load_all_documents(self):
        """Load all documents from disk on startup."""
        for doc_file in DOCUMENTS_DIR.glob('*.json'):
            try:
                doc_id = doc_file.stem
                with open(doc_file, 'r') as f:
                    data = json.load(f)
                    doc = Document(
                        doc_id,
                        content=data.get('content', ''),
                        version=data.get('version', 0)
                    )
                    self.documents[doc_id] = doc
                logger.info(f'Loaded document: {doc_id}')
            except Exception as e:
                logger.error(f'Failed to load {doc_file}: {e}')


class EditLogger:
    """Logs all edits in JSONL format for replay and audit."""
    
    def __init__(self):
        self.loggers = {}  # Per-document loggers
        self.lock = Lock()
    
    def log_edit(self, doc_id, user_id, edit_id, content, timestamp, version):
        """Append edit to JSONL log."""
        with self.lock:
            log_path = LOGS_DIR / f'{doc_id}.jsonl'
            log_entry = {
                'timestamp': timestamp,
                'user_id': user_id,
                'edit_id': edit_id,
                'version': version,
                'content_length': len(content),
                'event': 'edit'
            }
            with open(log_path, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')


class PresenceTracker:
    """Tracks active users per document."""
    
    def __init__(self):
        self.users_per_doc = defaultdict(set)
        self.session_to_user = {}  # session_id -> user_id
        self.lock = Lock()
    
    def join(self, doc_id, session_id, user_id):
        """Register user joining a document."""
        with self.lock:
            self.users_per_doc[doc_id].add(user_id)
            self.session_to_user[session_id] = (doc_id, user_id)
    
    def leave(self, session_id):
        """Unregister user leaving a document."""
        with self.lock:
            if session_id in self.session_to_user:
                doc_id, user_id = self.session_to_user[session_id]
                self.users_per_doc[doc_id].discard(user_id)
                del self.session_to_user[session_id]
    
    def get_presence(self, doc_id):
        """Get current user count and IDs for a document."""
        with self.lock:
            users = list(self.users_per_doc[doc_id])
            return {
                'count': len(users),
                'users': users
            }


class ConflictDetector:
    """Detects conflicts based on timestamp and affected lines."""
    
    CONFLICT_TIME_WINDOW = 1.0  # seconds
    
    def __init__(self):
        self.last_edits = defaultdict(lambda: {
            'timestamp': 0,
            'user_id': None,
            'lines': set()
        })
        self.lock = Lock()
    
    def detect_conflict(self, doc_id, timestamp, user_id, new_content, prev_content):
        """
        Detect if this edit conflicts with recent edits.
        Returns (is_conflict, affected_lines).
        """
        with self.lock:
            last_edit = self.last_edits[doc_id]
            time_diff = timestamp - last_edit['timestamp']
            
            # Check if within conflict window and different user
            if (time_diff <= self.CONFLICT_TIME_WINDOW and 
                last_edit['user_id'] and 
                last_edit['user_id'] != user_id):
                
                # Calculate affected lines
                new_lines = set(range(len(new_content.split('\n'))))
                prev_lines = set(range(len(prev_content.split('\n'))))
                affected_lines = new_lines | prev_lines
                
                # Check for overlap with previous edit
                if affected_lines & last_edit['lines']:
                    return True, list(affected_lines)
            
            # Update last edit info
            self.last_edits[doc_id] = {
                'timestamp': timestamp,
                'user_id': user_id,
                'lines': set(range(len(new_content.split('\n'))))
            }
            return False, []
    
    def reset_for_doc(self, doc_id):
        """Reset conflict state for a document."""
        with self.lock:
            self.last_edits[doc_id] = {
                'timestamp': 0,
                'user_id': None,
                'lines': set()
            }


# Initialize managers
doc_manager = DocumentManager()
edit_logger = EditLogger()
presence_tracker = PresenceTracker()
conflict_detector = ConflictDetector()

# ============================================================================
# Flask Routes
# ============================================================================

@app.route('/')
def index():
    """Serve the main collaboration page."""
    return render_template('index.html')


@app.route('/api/documents', methods=['GET'])
def list_documents():
    """List all available documents."""
    docs = [doc_manager.documents[doc_id].to_dict() 
            for doc_id in doc_manager.documents]
    return jsonify({'documents': docs})


@app.route('/api/documents', methods=['POST'])
def create_document():
    """Create a new document."""
    doc_id = str(uuid.uuid4())[:8]
    doc = doc_manager.get_or_create(doc_id)
    doc_manager.save_document(doc_id)
    return jsonify(doc.to_dict()), 201


@app.route('/api/documents/<doc_id>', methods=['GET'])
def get_document(doc_id):
    """Get document content."""
    doc = doc_manager.get_or_create(doc_id)
    return jsonify(doc.to_dict())


# ============================================================================
# WebSocket Events
# ============================================================================

@socketio.on('connect')
def handle_connect():
    """Handle new client connection."""
    user_id = f'user-{str(uuid.uuid4())[:6]}'
    logger.info(f'Client connected: {user_id} (sid: {request.sid})')
    
    emit('user_id', {'user_id': user_id})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    presence_tracker.leave(request.sid)
    logger.info(f'Client disconnected: {request.sid}')


@socketio.on('join_document')
def handle_join_document(data):
    """Handle user joining a document."""
    doc_id = data.get('doc_id')
    user_id = data.get('user_id')
    
    # Join the room
    join_room(doc_id)
    
    # Register presence
    presence_tracker.join(doc_id, request.sid, user_id)
    
    # Get document
    doc = doc_manager.get_or_create(doc_id)
    presence = presence_tracker.get_presence(doc_id)
    
    logger.info(f'{user_id} joined document {doc_id}. Presence: {presence["count"]}')
    
    # Send document state to joining client
    emit('document_loaded', {
        'doc_id': doc_id,
        'content': doc.content,
        'version': doc.version
    })
    
    # Broadcast presence update
    emit('presence_updated', presence, room=doc_id)


@socketio.on('edit')
def handle_edit(data):
    """Handle document edit event."""
    doc_id = data.get('doc_id')
    user_id = data.get('user_id')
    new_content = data.get('content', '')
    timestamp = data.get('timestamp', time.time())
    edit_id = data.get('edit_id', str(uuid.uuid4()))
    
    doc = doc_manager.get_or_create(doc_id)
    prev_content = doc.content
    
    # Detect conflict
    is_conflict, affected_lines = conflict_detector.detect_conflict(
        doc_id, timestamp, user_id, new_content, prev_content
    )
    
    # Apply Last-Write-Wins update
    doc.update(new_content, user_id, edit_id, timestamp)
    doc_manager.save_document(doc_id)
    
    # Log the edit
    edit_logger.log_edit(doc_id, user_id, edit_id, new_content, timestamp, doc.version)
    
    logger.info(f'{user_id} edited {doc_id} (v{doc.version}). Conflict: {is_conflict}')
    
    # Broadcast update to all clients in room
    emit('document_updated', {
        'doc_id': doc_id,
        'content': new_content,
        'version': doc.version,
        'user_id': user_id,
        'timestamp': timestamp,
        'edit_id': edit_id
    }, room=doc_id)
    
    # Broadcast conflict event if detected
    if is_conflict:
        emit('conflict_detected', {
            'doc_id': doc_id,
            'timestamp': timestamp,
            'user_id': user_id,
            'affected_lines': affected_lines,
            'version': doc.version
        }, room=doc_id)


@socketio.on('get_presence')
def handle_get_presence(data):
    """Get current presence info for a document."""
    doc_id = data.get('doc_id')
    presence = presence_tracker.get_presence(doc_id)
    emit('presence_updated', presence)


@socketio.on('request_history')
def handle_request_history(data):
    """Send edit history for a document."""
    doc_id = data.get('doc_id')
    doc = doc_manager.get_or_create(doc_id)
    
    # Read JSONL log if exists
    log_path = LOGS_DIR / f'{doc_id}.jsonl'
    history = []
    if log_path.exists():
        with open(log_path, 'r') as f:
            for line in f:
                try:
                    history.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    
    emit('history_loaded', {
        'doc_id': doc_id,
        'history': history,
        'edit_count': len(history)
    })


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors."""
    logger.error(f'Server error: {error}')
    return jsonify({'error': 'Server error'}), 500


# ============================================================================
# Application Entry Point
# ============================================================================

if __name__ == '__main__':
    logger.info('Starting Lightweight Collaboration Platform...')
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
