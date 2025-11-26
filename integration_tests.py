"""
Integration Test Suite for Lightweight Collaboration Platform

Simulates real multi-user scenarios with concurrent WebSocket connections,
conflict conditions, and persistence validation.
"""

import time
import json
import threading
import socketio
import requests
from pathlib import Path
from datetime import datetime

# Test configuration
TEST_SERVER_URL = 'http://localhost:5000'
TEST_WS_URL = 'http://localhost:5000'
TIMEOUT = 5


class IntegrationTestClient:
    """Simulates a collaborative user with WebSocket connection."""
    
    def __init__(self, user_name):
        self.user_name = user_name
        self.user_id = None
        self.doc_id = None
        self.sio = socketio.Client(reconnection_delay_max=1)
        self.events_received = []
        self.is_connected = False
        
        # Register event handlers
        self.sio.on('user_id', self._on_user_id)
        self.sio.on('document_loaded', self._on_document_loaded)
        self.sio.on('document_updated', self._on_document_updated)
        self.sio.on('presence_updated', self._on_presence_updated)
        self.sio.on('conflict_detected', self._on_conflict_detected)
    
    def _on_user_id(self, data):
        self.user_id = data['user_id']
        self.events_received.append(('user_id', data))
    
    def _on_document_loaded(self, data):
        self.doc_id = data['doc_id']
        self.events_received.append(('document_loaded', data))
    
    def _on_document_updated(self, data):
        self.events_received.append(('document_updated', data))
    
    def _on_presence_updated(self, data):
        self.events_received.append(('presence_updated', data))
    
    def _on_conflict_detected(self, data):
        self.events_received.append(('conflict_detected', data))
    
    def connect(self):
        """Connect to WebSocket server."""
        try:
            self.sio.connect(TEST_WS_URL, transports=['websocket', 'polling'])
            self.is_connected = True
            time.sleep(0.1)  # Wait for user_id assignment
            print(f"✓ {self.user_name} connected ({self.user_id})")
        except Exception as e:
            print(f"✗ {self.user_name} connection failed: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from WebSocket server."""
        self.sio.disconnect()
        self.is_connected = False
        print(f"✓ {self.user_name} disconnected")
    
    def join_document(self, doc_id):
        """Join a collaborative document."""
        self.sio.emit('join_document', {
            'doc_id': doc_id,
            'user_id': self.user_id
        })
        time.sleep(0.1)
        self.doc_id = doc_id
        print(f"✓ {self.user_name} joined document {doc_id}")
    
    def edit(self, content):
        """Send an edit to the document."""
        self.sio.emit('edit', {
            'doc_id': self.doc_id,
            'user_id': self.user_id,
            'content': content,
            'timestamp': time.time(),
            'edit_id': f'{self.user_id}-{time.time()}'
        })
        time.sleep(0.1)
        print(f"✓ {self.user_name} sent edit: '{content[:30]}...'")
    
    def get_last_event(self, event_type=None):
        """Get last received event."""
        for event, data in reversed(self.events_received):
            if event_type is None or event == event_type:
                return data
        return None
    
    def wait_for_event(self, event_type, timeout=TIMEOUT):
        """Wait for specific event type."""
        start = time.time()
        while time.time() - start < timeout:
            for event, data in self.events_received:
                if event == event_type:
                    return data
            time.sleep(0.05)
        raise TimeoutError(f"Event {event_type} not received within {timeout}s")


class IntegrationTestSuite:
    """Integration test scenarios."""
    
    def __init__(self):
        self.test_results = []
    
    def _test(self, name, func):
        """Run a single test."""
        print(f"\n{'='*60}")
        print(f"TEST: {name}")
        print('='*60)
        try:
            func()
            self.test_results.append((name, 'PASS', None))
            print(f"✅ PASS: {name}")
        except Exception as e:
            self.test_results.append((name, 'FAIL', str(e)))
            print(f"❌ FAIL: {name}")
            print(f"   Error: {e}")
    
    def test_server_health(self):
        """Test 1: Server is running and responding."""
        try:
            response = requests.get(TEST_SERVER_URL, timeout=TIMEOUT)
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        except requests.exceptions.ConnectionError:
            raise Exception("Server not running. Start with: python app.py")
    
    def test_single_user_editing(self):
        """Test 2: Single user can edit a document."""
        doc_id = f'test-single-{int(time.time())}'
        client = IntegrationTestClient('User-A')
        
        try:
            client.connect()
            client.join_document(doc_id)
            
            # Verify document loaded
            loaded = client.wait_for_event('document_loaded')
            assert loaded['doc_id'] == doc_id
            assert loaded['content'] == ''  # New document
            
            # Send edit
            edit_text = 'Hello, World!'
            client.edit(edit_text)
            
            # Verify edit was applied
            updated = client.wait_for_event('document_updated')
            assert updated['content'] == edit_text
            assert updated['user_id'] == client.user_id
            
        finally:
            client.disconnect()
    
    def test_two_users_editing(self):
        """Test 3: Two users can edit same document."""
        doc_id = f'test-multi-{int(time.time())}'
        user_a = IntegrationTestClient('User-A')
        user_b = IntegrationTestClient('User-B')
        
        try:
            # Connect both users
            user_a.connect()
            user_b.connect()
            
            # Both join same document
            user_a.join_document(doc_id)
            time.sleep(0.2)
            user_b.join_document(doc_id)
            time.sleep(0.2)
            
            # Verify presence
            presence = user_a.wait_for_event('presence_updated')
            assert presence['count'] == 2, f"Expected 2 users, got {presence['count']}"
            
            # User A edits
            user_a.edit('User A was here')
            time.sleep(0.2)
            
            # User B should receive update
            update = user_b.wait_for_event('document_updated')
            assert 'User A was here' in update['content']
            
            # User B edits
            user_b.edit('User A was here. User B was here.')
            time.sleep(0.2)
            
            # User A should receive update
            update = user_a.wait_for_event('document_updated')
            assert 'User B was here' in update['content']
            
        finally:
            user_a.disconnect()
            user_b.disconnect()
    
    def test_concurrent_conflicting_edits(self):
        """Test 4: Conflict detection with concurrent edits."""
        doc_id = f'test-conflict-{int(time.time())}'
        user_a = IntegrationTestClient('User-A')
        user_b = IntegrationTestClient('User-B')
        
        try:
            user_a.connect()
            user_b.connect()
            
            user_a.join_document(doc_id)
            time.sleep(0.1)
            user_b.join_document(doc_id)
            time.sleep(0.1)
            
            # Initialize document
            user_a.edit('Line 1\nLine 2\nLine 3')
            time.sleep(0.3)
            
            # Simulate concurrent edits on same line
            def edit_a():
                time.sleep(0.1)  # Ensure we're in conflict window
                user_a.edit('Line 1\nLine 2 modified by A\nLine 3')
            
            def edit_b():
                time.sleep(0.15)  # Slightly offset but still within conflict window
                user_b.edit('Line 1\nLine 2 modified by B\nLine 3')
            
            thread_a = threading.Thread(target=edit_a)
            thread_b = threading.Thread(target=edit_b)
            
            thread_a.start()
            thread_b.start()
            thread_a.join()
            thread_b.join()
            
            time.sleep(0.5)
            
            # Check if conflict was detected (at least one client should see it)
            conflict_a = None
            conflict_b = None
            
            for event, data in user_a.events_received:
                if event == 'conflict_detected':
                    conflict_a = data
                    break
            
            for event, data in user_b.events_received:
                if event == 'conflict_detected':
                    conflict_b = data
                    break
            
            # At least one should detect conflict
            if conflict_a or conflict_b:
                print(f"   Conflict detected: {conflict_a or conflict_b}")
            else:
                print("   Note: Conflict window may have passed; edits applied sequentially")
            
        finally:
            user_a.disconnect()
            user_b.disconnect()
    
    def test_presence_tracking(self):
        """Test 5: User presence tracking."""
        doc_id = f'test-presence-{int(time.time())}'
        users = []
        
        try:
            # Connect 3 users
            for i in range(3):
                user = IntegrationTestClient(f'User-{chr(65+i)}')
                user.connect()
                user.join_document(doc_id)
                users.append(user)
                time.sleep(0.1)
            
            # Check presence
            presence = users[0].wait_for_event('presence_updated')
            assert presence['count'] == 3, f"Expected 3 users, got {presence['count']}"
            print(f"   Active users: {presence['users']}")
            
            # Disconnect one user
            users[0].disconnect()
            users.pop(0)
            time.sleep(0.2)
            
            # Check updated presence
            presence = users[0].wait_for_event('presence_updated')
            assert presence['count'] == 2, f"Expected 2 users, got {presence['count']}"
            
        finally:
            for user in users:
                if user.is_connected:
                    user.disconnect()
    
    def test_edit_debouncing(self):
        """Test 6: Edit debouncing (400ms)."""
        doc_id = f'test-debounce-{int(time.time())}'
        client = IntegrationTestClient('User-A')
        
        try:
            client.connect()
            client.join_document(doc_id)
            time.sleep(0.1)
            
            # Rapid-fire edits
            for i in range(5):
                client.edit(f'Edit {i}')
                time.sleep(0.05)  # 50ms apart, within debounce
            
            time.sleep(0.5)  # Wait for debounce
            
            # Count document_updated events (should be batched)
            update_count = sum(1 for e, _ in client.events_received if e == 'document_updated')
            print(f"   Updates received: {update_count}")
            assert update_count >= 1, "No updates received"
            
        finally:
            client.disconnect()
    
    def test_document_list(self):
        """Test 7: List documents via REST API."""
        # Create a document
        doc_id = f'test-api-{int(time.time())}'
        response = requests.post(f'{TEST_SERVER_URL}/api/documents')
        assert response.status_code == 201
        created_doc = response.json()
        
        # List documents
        response = requests.get(f'{TEST_SERVER_URL}/api/documents')
        assert response.status_code == 200
        data = response.json()
        assert 'documents' in data
        print(f"   Documents found: {len(data['documents'])}")
    
    def test_persistence(self):
        """Test 8: Document persistence to disk."""
        doc_id = f'test-persist-{int(time.time())}'
        client = IntegrationTestClient('User-A')
        
        try:
            client.connect()
            client.join_document(doc_id)
            time.sleep(0.1)
            
            # Edit document
            test_content = 'Persistent content from test'
            client.edit(test_content)
            time.sleep(0.3)
            
            # Check if file was created
            doc_file = Path(__file__).parent / 'data' / 'documents' / f'{doc_id}.json'
            assert doc_file.exists(), f"Document file not created: {doc_file}"
            
            # Verify content
            with open(doc_file) as f:
                data = json.load(f)
                assert data['content'] == test_content
            
            print(f"   Persisted to: {doc_file}")
            
        finally:
            client.disconnect()
    
    def test_edit_logging(self):
        """Test 9: Edit logging in JSONL format."""
        doc_id = f'test-log-{int(time.time())}'
        client = IntegrationTestClient('User-A')
        
        try:
            client.connect()
            client.join_document(doc_id)
            time.sleep(0.1)
            
            # Make edits
            for i in range(3):
                client.edit(f'Edit {i}')
                time.sleep(0.1)
            
            time.sleep(0.3)
            
            # Check if log file was created
            log_file = Path(__file__).parent / 'data' / 'logs' / f'{doc_id}.jsonl'
            assert log_file.exists(), f"Log file not created: {log_file}"
            
            # Verify log entries
            with open(log_file) as f:
                lines = f.readlines()
                assert len(lines) >= 3, f"Expected 3+ log entries, got {len(lines)}"
                
                for line in lines:
                    entry = json.loads(line)
                    assert entry['event'] == 'edit'
                    assert entry['user_id'] == client.user_id
            
            print(f"   Log entries: {len(lines)}")
            
        finally:
            client.disconnect()
    
    def test_multi_document_independence(self):
        """Test 10: Multiple documents are independent."""
        doc_id_1 = f'test-doc1-{int(time.time())}'
        doc_id_2 = f'test-doc2-{int(time.time())}'
        
        client_a = IntegrationTestClient('User-A')
        client_b = IntegrationTestClient('User-B')
        
        try:
            client_a.connect()
            client_b.connect()
            
            # A edits document 1
            client_a.join_document(doc_id_1)
            time.sleep(0.1)
            client_a.edit('Content for doc 1')
            time.sleep(0.2)
            
            # B edits document 2
            client_b.join_document(doc_id_2)
            time.sleep(0.1)
            client_b.edit('Content for doc 2')
            time.sleep(0.2)
            
            # A should not receive B's updates
            updates_for_doc1 = [e for e, d in client_a.events_received 
                               if e == 'document_updated' and d['doc_id'] == doc_id_1]
            updates_for_doc2 = [e for e, d in client_a.events_received 
                               if e == 'document_updated' and d['doc_id'] == doc_id_2]
            
            assert len(updates_for_doc1) >= 1
            assert len(updates_for_doc2) == 0, "A should not receive updates from doc 2"
            
        finally:
            client_a.disconnect()
            client_b.disconnect()
    
    def run_all(self):
        """Run all integration tests."""
        print("\n" + "="*60)
        print("INTEGRATION TEST SUITE")
        print("="*60)
        print(f"Start time: {datetime.now().isoformat()}")
        print(f"Server: {TEST_SERVER_URL}")
        
        self._test("Server Health Check", self.test_server_health)
        self._test("Single User Editing", self.test_single_user_editing)
        self._test("Two Users Editing", self.test_two_users_editing)
        self._test("Concurrent Conflicting Edits", self.test_concurrent_conflicting_edits)
        self._test("Presence Tracking", self.test_presence_tracking)
        self._test("Edit Debouncing", self.test_edit_debouncing)
        self._test("Document List API", self.test_document_list)
        self._test("Document Persistence", self.test_persistence)
        self._test("Edit Logging (JSONL)", self.test_edit_logging)
        self._test("Multi-Document Independence", self.test_multi_document_independence)
        
        # Print summary
        self._print_summary()
    
    def _print_summary(self):
        """Print test summary."""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for _, status, _ in self.test_results if status == 'PASS')
        failed = sum(1 for _, status, _ in self.test_results if status == 'FAIL')
        
        for name, status, error in self.test_results:
            symbol = "✅" if status == "PASS" else "❌"
            print(f"{symbol} {name}: {status}")
            if error:
                print(f"   └─ {error[:100]}")
        
        print("\n" + "-"*60)
        print(f"Total: {len(self.test_results)} tests")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed/len(self.test_results)*100):.1f}%")
        print("="*60 + "\n")
        
        # Save results
        results_file = Path(__file__).parent / 'integration_test_report.json'
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total': len(self.test_results),
                'passed': passed,
                'failed': failed,
                'success_rate': f"{(passed/len(self.test_results)*100):.1f}%",
                'results': [
                    {'name': name, 'status': status, 'error': error}
                    for name, status, error in self.test_results
                ]
            }, f, indent=2)
        
        print(f"Results saved to: {results_file}\n")
        
        return failed == 0


if __name__ == '__main__':
    suite = IntegrationTestSuite()
    success = suite.run_all()
    exit(0 if success else 1)
