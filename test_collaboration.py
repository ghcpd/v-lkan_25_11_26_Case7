"""
Automated Test Suite for Collaborative Document Editor
Tests real-time collaboration, persistence, conflict handling, and multi-document scenarios
"""

import pytest
import time
import json
import os
import shutil
from socketio import SimpleClient
from app import app, socketio, doc_manager, LOGS_DIR, DATA_DIR
from threading import Thread
import requests

# Test configuration
BASE_URL = 'http://localhost:5000'
SOCKETIO_URL = 'http://localhost:5000'

class TestClient:
    """Wrapper for Socket.IO test client"""
    
    def __init__(self, url=SOCKETIO_URL):
        self.client = SimpleClient()
        self.url = url
        self.user_id = None
        self.events = []
        
    def connect(self):
        """Connect to Socket.IO server"""
        self.client.connect(self.url)
        
        # Wait for user_assigned event
        event = self.client.receive()
        if event[0] == 'user_assigned':
            self.user_id = event[1]['user_id']
        
        return self.user_id
    
    def disconnect(self):
        """Disconnect from server"""
        self.client.disconnect()
    
    def emit(self, event_name, data=None):
        """Emit an event"""
        self.client.emit(event_name, data)
    
    def receive(self, timeout=2):
        """Receive an event"""
        try:
            event = self.client.receive(timeout=timeout)
            self.events.append(event)
            return event
        except Exception as e:
            return None
    
    def wait_for_event(self, event_name, timeout=5):
        """Wait for a specific event"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            event = self.receive(timeout=1)
            if event and event[0] == event_name:
                return event
        
        return None

@pytest.fixture(scope='session')
def server():
    """Start the Flask server in a background thread"""
    def run_server():
        socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
    
    server_thread = Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    time.sleep(2)
    
    yield
    
    # Cleanup is handled by daemon thread

@pytest.fixture
def clean_data():
    """Clean data directory before and after tests"""
    if os.path.exists(DATA_DIR):
        shutil.rmtree(DATA_DIR)
    os.makedirs(LOGS_DIR, exist_ok=True)
    
    yield
    
    # Optional: keep data for inspection
    # if os.path.exists(DATA_DIR):
    #     shutil.rmtree(DATA_DIR)

class TestDocumentCreation:
    """Test document creation and retrieval"""
    
    def test_create_document_api(self, server):
        """Test creating a document via API"""
        response = requests.post(f'{BASE_URL}/api/documents')
        assert response.status_code == 200
        
        data = response.json()
        assert 'doc_id' in data
        assert 'content' in data
        assert 'version' in data
        assert data['version'] == 0
        assert data['content'] == ''
    
    def test_get_document_api(self, server):
        """Test retrieving a document via API"""
        # Create document first
        create_response = requests.post(f'{BASE_URL}/api/documents')
        doc_id = create_response.json()['doc_id']
        
        # Get document
        get_response = requests.get(f'{BASE_URL}/api/documents/{doc_id}')
        assert get_response.status_code == 200
        
        data = get_response.json()
        assert data['doc_id'] == doc_id
        assert 'content' in data
        assert 'version' in data
        assert 'user_count' in data
    
    def test_get_nonexistent_document_creates_it(self, server):
        """Test that getting a non-existent document creates it"""
        doc_id = 'test-doc-123'
        response = requests.get(f'{BASE_URL}/api/documents/{doc_id}')
        
        assert response.status_code == 200
        data = response.json()
        assert data['doc_id'] == doc_id
        assert data['version'] == 0

class TestRealtimeCollaboration:
    """Test real-time collaboration features"""
    
    def test_single_user_connection(self, server, clean_data):
        """Test single user connecting and joining document"""
        client = TestClient()
        user_id = client.connect()
        
        assert user_id is not None
        assert user_id.startswith('user-')
        
        # Join document
        client.emit('join_document', {'doc_id': 'test-doc'})
        
        # Wait for document state
        event = client.wait_for_event('document_state')
        assert event is not None
        assert event[0] == 'document_state'
        
        data = event[1]
        assert 'content' in data
        assert 'version' in data
        assert 'user_count' in data
        assert data['user_count'] == 1
        
        client.disconnect()
    
    def test_multi_user_collaboration(self, server, clean_data):
        """Test multiple users collaborating on same document"""
        client1 = TestClient()
        client2 = TestClient()
        
        user1_id = client1.connect()
        user2_id = client2.connect()
        
        # Both join same document
        client1.emit('join_document', {'doc_id': 'collab-test'})
        event1 = client1.wait_for_event('document_state')
        assert event1[1]['user_count'] == 1
        
        client2.emit('join_document', {'doc_id': 'collab-test'})
        event2 = client2.wait_for_event('document_state')
        assert event2[1]['user_count'] == 2
        
        # Client1 should receive user_joined event
        join_event = client1.wait_for_event('user_joined')
        assert join_event is not None
        assert join_event[1]['user_id'] == user2_id
        assert join_event[1]['user_count'] == 2
        
        # Client1 edits document
        client1.emit('edit_document', {
            'content': 'Hello from user 1',
            'cursor_position': 0
        })
        
        # Client2 should receive update
        update_event = client2.wait_for_event('document_updated')
        assert update_event is not None
        assert update_event[1]['content'] == 'Hello from user 1'
        assert update_event[1]['user_id'] == user1_id
        
        client1.disconnect()
        client2.disconnect()
    
    def test_user_presence_tracking(self, server, clean_data):
        """Test user presence awareness"""
        clients = [TestClient() for _ in range(3)]
        
        # Connect all clients
        for client in clients:
            client.connect()
            client.emit('join_document', {'doc_id': 'presence-test'})
            time.sleep(0.2)
        
        # Check user count
        response = requests.get(f'{BASE_URL}/api/documents/presence-test')
        data = response.json()
        assert data['user_count'] == 3
        
        # Disconnect one client
        clients[0].disconnect()
        time.sleep(0.5)
        
        # Check updated count
        response = requests.get(f'{BASE_URL}/api/documents/presence-test')
        data = response.json()
        assert data['user_count'] == 2
        
        for client in clients[1:]:
            client.disconnect()

class TestPersistence:
    """Test persistent storage and edit logging"""
    
    def test_edit_logging(self, server, clean_data):
        """Test that edits are logged to JSONL file"""
        client = TestClient()
        client.connect()
        
        doc_id = 'log-test'
        client.emit('join_document', {'doc_id': doc_id})
        client.wait_for_event('document_state')
        
        # Make several edits
        edits = [
            'First edit',
            'Second edit',
            'Third edit'
        ]
        
        for content in edits:
            client.emit('edit_document', {'content': content})
            # Wait for server to process
            time.sleep(1.0)
        
        client.disconnect()
        time.sleep(2.0)  # Increased delay for file writes to complete
        
        # Check log file exists
        log_path = os.path.join(LOGS_DIR, f'{doc_id}.jsonl')
        assert os.path.exists(log_path)
        
        # Read and verify log entries
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Should have create + 3 edit entries
        assert len(lines) >= 4
        
        # Verify edit entries
        edit_count = 0
        for line in lines:
            record = json.loads(line)
            if record['action'] == 'edit':
                edit_count += 1
                assert 'user_id' in record
                assert 'content' in record
                assert 'version' in record
                assert 'timestamp' in record
        
        assert edit_count == 3
    
    def test_document_recovery_on_startup(self, server, clean_data):
        """Test document state recovery from logs"""
        # Create document and make edits
        client = TestClient()
        client.connect()
        
        doc_id = 'recovery-test'
        client.emit('join_document', {'doc_id': doc_id})
        client.wait_for_event('document_state')
        
        final_content = 'This is the final content'
        client.emit('edit_document', {'content': final_content})
        time.sleep(2.0)  # Wait for edit to be fully processed
        
        client.disconnect()
        time.sleep(1.0)  # Wait for cleanup
        
        # Simulate server restart by rebuilding documents
        doc_manager.documents.clear()
        doc_manager.load_documents()
        
        # Verify document was recovered
        assert doc_id in doc_manager.documents
        assert doc_manager.documents[doc_id]['content'] == final_content
        assert doc_manager.documents[doc_id]['version'] >= 1
    
    def test_version_incrementing(self, server, clean_data):
        """Test that version numbers increment correctly"""
        client = TestClient()
        client.connect()
        
        doc_id = 'version-test'
        client.emit('join_document', {'doc_id': doc_id})
        event = client.wait_for_event('document_state')
        initial_version = event[1]['version']
        
        # Make 5 edits
        for i in range(5):
            client.emit('edit_document', {'content': f'Edit {i+1}'})
            time.sleep(0.5)  # Increased delay for each edit
        
        client.disconnect()
        time.sleep(1.0)  # Increased delay for processing
        
        # Check final version
        response = requests.get(f'{BASE_URL}/api/documents/{doc_id}')
        final_version = response.json()['version']
        
        assert final_version == initial_version + 5

class TestConflictDetection:
    """Test conflict detection and visualization"""
    
    def test_concurrent_edit_conflict(self, server, clean_data):
        """Test conflict detection on concurrent edits"""
        client1 = TestClient()
        client2 = TestClient()
        
        client1.connect()
        client2.connect()
        
        doc_id = 'conflict-test'
        
        # Both join same document
        client1.emit('join_document', {'doc_id': doc_id})
        client1.wait_for_event('document_state')
        
        client2.emit('join_document', {'doc_id': doc_id})
        client2.wait_for_event('document_state')
        client1.wait_for_event('user_joined')
        
        # Both edit simultaneously
        client1.emit('edit_document', {'content': 'User 1 content'})
        time.sleep(0.1)
        client2.emit('edit_document', {'content': 'User 2 content'})
        
        # Wait for conflict detection
        time.sleep(0.5)
        
        # At least one client should receive conflict event
        conflict1 = client1.wait_for_event('conflict_detected')
        conflict2 = client2.wait_for_event('conflict_detected')
        
        # One of them should have detected conflict
        assert conflict1 is not None or conflict2 is not None
        
        client1.disconnect()
        client2.disconnect()
    
    def test_no_conflict_same_user(self, server, clean_data):
        """Test that same user edits don't trigger conflicts"""
        client = TestClient()
        client.connect()
        
        doc_id = 'no-conflict-test'
        client.emit('join_document', {'doc_id': doc_id})
        client.wait_for_event('document_state')
        
        # Make rapid edits from same user
        for i in range(5):
            client.emit('edit_document', {'content': f'Edit {i}'})
            time.sleep(0.1)
        
        # Should not receive conflict events
        conflict = client.wait_for_event('conflict_detected')
        assert conflict is None
        
        client.disconnect()

class TestMultiDocument:
    """Test multi-document scenarios"""
    
    def test_multiple_independent_documents(self, server, clean_data):
        """Test multiple documents operating independently"""
        # Create 3 documents
        doc_ids = []
        for i in range(3):
            response = requests.post(f'{BASE_URL}/api/documents')
            doc_ids.append(response.json()['doc_id'])
        
        # Edit each document independently
        for i, doc_id in enumerate(doc_ids):
            client = TestClient()
            client.connect()
            client.emit('join_document', {'doc_id': doc_id})
            client.wait_for_event('document_state')
            client.emit('edit_document', {'content': f'Content for doc {i+1}'})
            time.sleep(0.3)
            client.disconnect()
        
        # Verify each document has correct content
        for i, doc_id in enumerate(doc_ids):
            response = requests.get(f'{BASE_URL}/api/documents/{doc_id}')
            data = response.json()
            assert data['content'] == f'Content for doc {i+1}'
    
    def test_user_switching_documents(self, server, clean_data):
        """Test user switching between documents"""
        client = TestClient()
        client.connect()
        
        # Join first document
        client.emit('join_document', {'doc_id': 'doc1'})
        event1 = client.wait_for_event('document_state')
        assert event1 is not None
        
        # Edit first document
        client.emit('edit_document', {'content': 'First document'})
        time.sleep(0.3)
        
        # Switch to second document
        client.emit('join_document', {'doc_id': 'doc2'})
        event2 = client.wait_for_event('document_state')
        assert event2 is not None
        
        # Edit second document
        client.emit('edit_document', {'content': 'Second document'})
        time.sleep(0.3)
        
        client.disconnect()
        
        # Verify both documents
        response1 = requests.get(f'{BASE_URL}/api/documents/doc1')
        response2 = requests.get(f'{BASE_URL}/api/documents/doc2')
        
        assert response1.json()['content'] == 'First document'
        assert response2.json()['content'] == 'Second document'

class TestVersionHistory:
    """Test version history functionality"""
    
    def test_history_retrieval(self, server, clean_data):
        """Test retrieving edit history"""
        client = TestClient()
        client.connect()
        
        doc_id = 'history-test'
        client.emit('join_document', {'doc_id': doc_id})
        client.wait_for_event('document_state')
        
        # Make several edits
        for i in range(3):
            client.emit('edit_document', {'content': f'Version {i+1}'})
            time.sleep(0.3)
        
        # Request history
        client.emit('request_history', {'doc_id': doc_id})
        history_event = client.wait_for_event('history_response')
        
        assert history_event is not None
        history = history_event[1]['history']
        
        assert len(history) == 3
        for entry in history:
            assert 'user_id' in entry
            assert 'version' in entry
            assert 'timestamp' in entry
            assert 'preview' in entry
        
        client.disconnect()

class TestLastWriteWins:
    """Test Last-Write-Wins conflict resolution strategy"""
    
    def test_lww_resolution(self, server, clean_data):
        """Test that last write wins in concurrent scenarios"""
        client1 = TestClient()
        client2 = TestClient()
        
        client1.connect()
        client2.connect()
        
        doc_id = 'lww-test'
        
        # Both join document
        client1.emit('join_document', {'doc_id': doc_id})
        client1.wait_for_event('document_state')
        
        client2.emit('join_document', {'doc_id': doc_id})
        client2.wait_for_event('document_state')
        client1.wait_for_event('user_joined')
        
        # Client 1 writes
        client1.emit('edit_document', {'content': 'First write'})
        time.sleep(0.2)
        
        # Client 2 writes (should win)
        client2.emit('edit_document', {'content': 'Second write wins'})
        time.sleep(0.5)
        
        # Verify final state
        response = requests.get(f'{BASE_URL}/api/documents/{doc_id}')
        final_content = response.json()['content']
        
        assert final_content == 'Second write wins'
        
        client1.disconnect()
        client2.disconnect()

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
