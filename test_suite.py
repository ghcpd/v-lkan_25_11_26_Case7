"""
Automated Test Suite for Lightweight Collaboration Platform

Tests cover:
1. Real-time collaboration (multi-user edits)
2. Persistence (document storage and replay)
3. Conflict handling (LWW, conflict detection)
4. Multi-document behavior (independent sessions)
5. Presence tracking (user join/leave)
"""

import unittest
import time
import json
import tempfile
import shutil
import threading
from pathlib import Path
from datetime import datetime

# Mock the Flask app for testing
import sys
sys.path.insert(0, str(Path(__file__).parent))

from app import (
    Document, DocumentManager, EditLogger, PresenceTracker, 
    ConflictDetector, DATA_DIR, DOCUMENTS_DIR, LOGS_DIR
)


class TestDocument(unittest.TestCase):
    """Test Document class."""
    
    def test_document_creation(self):
        """Test creating a new document."""
        doc = Document('test-1', 'Hello World', version=0)
        self.assertEqual(doc.id, 'test-1')
        self.assertEqual(doc.content, 'Hello World')
        self.assertEqual(doc.version, 0)
    
    def test_document_update(self):
        """Test updating document content."""
        doc = Document('test-2')
        doc.update('New content', 'user-1', 'edit-1', time.time())
        self.assertEqual(doc.content, 'New content')
        self.assertEqual(doc.version, 1)
        self.assertEqual(len(doc.edit_history), 1)
    
    def test_document_serialization(self):
        """Test document to_dict conversion."""
        doc = Document('test-3', 'Content', version=5)
        data = doc.to_dict()
        self.assertEqual(data['id'], 'test-3')
        self.assertEqual(data['content'], 'Content')
        self.assertEqual(data['version'], 5)


class TestDocumentManager(unittest.TestCase):
    """Test DocumentManager class."""
    
    def setUp(self):
        """Set up test fixture."""
        self.manager = DocumentManager()
    
    def test_get_or_create_new(self):
        """Test creating a new document."""
        doc = self.manager.get_or_create('new-doc-1')
        self.assertEqual(doc.id, 'new-doc-1')
        self.assertEqual(doc.content, '')
    
    def test_get_existing(self):
        """Test retrieving existing document."""
        doc1 = self.manager.get_or_create('existing-1')
        doc1.update('Content A', 'user-1', 'edit-1', time.time())
        
        doc2 = self.manager.get_or_create('existing-1')
        self.assertEqual(doc2.content, 'Content A')
        self.assertEqual(doc1, doc2)  # Same object
    
    def test_save_document(self):
        """Test persisting document to disk."""
        doc = self.manager.get_or_create('save-test-1')
        doc.update('Saved content', 'user-1', 'edit-1', time.time())
        self.manager.save_document('save-test-1')
        
        # Verify file was created
        doc_file = DOCUMENTS_DIR / 'save-test-1.json'
        self.assertTrue(doc_file.exists())
        
        # Verify content
        with open(doc_file) as f:
            data = json.load(f)
            self.assertEqual(data['content'], 'Saved content')


class TestEditLogger(unittest.TestCase):
    """Test EditLogger class."""
    
    def setUp(self):
        """Set up test fixture."""
        self.logger = EditLogger()
    
    def test_log_edit(self):
        """Test logging an edit."""
        self.logger.log_edit('doc-1', 'user-1', 'edit-1', 'content', time.time(), 1)
        
        log_file = LOGS_DIR / 'doc-1.jsonl'
        self.assertTrue(log_file.exists())
        
        # Verify log entry
        with open(log_file) as f:
            entry = json.loads(f.readline())
            self.assertEqual(entry['user_id'], 'user-1')
            self.assertEqual(entry['edit_id'], 'edit-1')
            self.assertEqual(entry['event'], 'edit')
    
    def test_multiple_edits_logged(self):
        """Test logging multiple edits."""
        for i in range(3):
            self.logger.log_edit(f'doc-2', f'user-{i}', f'edit-{i}', 
                               f'content-{i}', time.time() + i, i + 1)
        
        log_file = LOGS_DIR / 'doc-2.jsonl'
        
        # Count entries
        with open(log_file) as f:
            count = len(f.readlines())
        self.assertEqual(count, 3)


class TestPresenceTracker(unittest.TestCase):
    """Test PresenceTracker class."""
    
    def setUp(self):
        """Set up test fixture."""
        self.tracker = PresenceTracker()
    
    def test_join_document(self):
        """Test user joining a document."""
        self.tracker.join('doc-1', 'session-1', 'user-1')
        presence = self.tracker.get_presence('doc-1')
        self.assertEqual(presence['count'], 1)
        self.assertIn('user-1', presence['users'])
    
    def test_multiple_users(self):
        """Test multiple users in same document."""
        self.tracker.join('doc-1', 'session-1', 'user-1')
        self.tracker.join('doc-1', 'session-2', 'user-2')
        self.tracker.join('doc-1', 'session-3', 'user-3')
        
        presence = self.tracker.get_presence('doc-1')
        self.assertEqual(presence['count'], 3)
    
    def test_leave_document(self):
        """Test user leaving a document."""
        self.tracker.join('doc-1', 'session-1', 'user-1')
        self.tracker.join('doc-1', 'session-2', 'user-2')
        
        self.tracker.leave('session-1')
        presence = self.tracker.get_presence('doc-1')
        self.assertEqual(presence['count'], 1)
        self.assertNotIn('user-1', presence['users'])
    
    def test_empty_presence(self):
        """Test presence with no users."""
        presence = self.tracker.get_presence('doc-1')
        self.assertEqual(presence['count'], 0)


class TestConflictDetector(unittest.TestCase):
    """Test ConflictDetector class."""
    
    def setUp(self):
        """Set up test fixture."""
        self.detector = ConflictDetector()
    
    def test_no_conflict_single_user(self):
        """Test no conflict with single user."""
        is_conflict, lines = self.detector.detect_conflict(
            'doc-1', time.time(), 'user-1', 'content-1', ''
        )
        self.assertFalse(is_conflict)
    
    def test_no_conflict_time_gap(self):
        """Test no conflict with large time gap."""
        now = time.time()
        
        # First edit
        self.detector.detect_conflict('doc-1', now, 'user-1', 'content-1', '')
        
        # Second edit after 2 seconds
        is_conflict, lines = self.detector.detect_conflict(
            'doc-1', now + 2.0, 'user-2', 'content-2', 'content-1'
        )
        self.assertFalse(is_conflict)
    
    def test_conflict_same_time_window(self):
        """Test conflict detection within time window."""
        now = time.time()
        
        # First edit by user-1
        self.detector.detect_conflict('doc-1', now, 'user-1', 'line1\nline2\nline3', '')
        
        # Second edit by user-2 within 1 second (conflict window)
        is_conflict, lines = self.detector.detect_conflict(
            'doc-1', now + 0.5, 'user-2', 'line1\nline2-modified\nline3', 'line1\nline2\nline3'
        )
        self.assertTrue(is_conflict)
        self.assertGreater(len(lines), 0)
    
    def test_no_conflict_same_user(self):
        """Test no conflict when same user edits twice."""
        now = time.time()
        
        # First edit
        self.detector.detect_conflict('doc-1', now, 'user-1', 'content-1', '')
        
        # Second edit by same user immediately after
        is_conflict, lines = self.detector.detect_conflict(
            'doc-1', now + 0.5, 'user-1', 'content-2', 'content-1'
        )
        self.assertFalse(is_conflict)


class TestRealTimeCollaboration(unittest.TestCase):
    """Test real-time collaboration scenarios."""
    
    def setUp(self):
        """Set up test fixture."""
        self.manager = DocumentManager()
        self.detector = ConflictDetector()
        self.logger = EditLogger()
    
    def test_sequential_edits(self):
        """Test sequential edits by different users."""
        doc = self.manager.get_or_create('collab-1')
        
        # User 1 edits
        now = time.time()
        doc.update('User 1 edit', 'user-1', 'edit-1', now)
        self.assertEqual(doc.content, 'User 1 edit')
        self.assertEqual(doc.version, 1)
        
        # User 2 edits
        doc.update('User 2 edit', 'user-2', 'edit-2', now + 2)
        self.assertEqual(doc.content, 'User 2 edit')  # Last-Write-Wins
        self.assertEqual(doc.version, 2)
    
    def test_concurrent_edits_lww(self):
        """Test Last-Write-Wins with concurrent edits."""
        doc = self.manager.get_or_create('collab-2')
        
        now = time.time()
        # Both edits at nearly same time, but with clear order
        doc.update('Edit A', 'user-1', 'edit-1', now + 0.1)
        doc.update('Edit B', 'user-2', 'edit-2', now + 0.2)  # Later timestamp wins
        
        self.assertEqual(doc.content, 'Edit B')
        self.assertEqual(doc.version, 2)
    
    def test_persistence_and_replay(self):
        """Test document persistence and replay."""
        doc_id = 'persist-1'
        
        # Create and edit document
        doc = self.manager.get_or_create(doc_id)
        doc.update('Initial content', 'user-1', 'edit-1', time.time())
        doc.update('Updated content', 'user-2', 'edit-2', time.time() + 1)
        self.manager.save_document(doc_id)
        
        # Create new manager instance (simulates restart)
        new_manager = DocumentManager()
        restored_doc = new_manager.get_or_create(doc_id)
        
        # Verify restored content
        self.assertEqual(restored_doc.content, 'Updated content')
        self.assertEqual(restored_doc.version, 2)


class TestMultiDocumentBehavior(unittest.TestCase):
    """Test behavior with multiple documents."""
    
    def setUp(self):
        """Set up test fixture."""
        self.manager = DocumentManager()
    
    def test_independent_documents(self):
        """Test that documents are independent."""
        doc1 = self.manager.get_or_create('multi-1')
        doc2 = self.manager.get_or_create('multi-2')
        
        doc1.update('Content 1', 'user-1', 'edit-1', time.time())
        doc2.update('Content 2', 'user-2', 'edit-2', time.time())
        
        self.assertEqual(doc1.content, 'Content 1')
        self.assertEqual(doc2.content, 'Content 2')
        self.assertEqual(doc1.version, 1)
        self.assertEqual(doc2.version, 1)
    
    def test_multiple_document_persistence(self):
        """Test persistence of multiple documents."""
        docs = {}
        for i in range(3):
            doc_id = f'multi-persist-{i}'
            doc = self.manager.get_or_create(doc_id)
            doc.update(f'Content {i}', f'user-{i}', f'edit-{i}', time.time())
            self.manager.save_document(doc_id)
            docs[doc_id] = doc
        
        # Reload and verify
        new_manager = DocumentManager()
        for doc_id, original_doc in docs.items():
            restored_doc = new_manager.get_or_create(doc_id)
            self.assertEqual(restored_doc.content, original_doc.content)


class TestThreadSafety(unittest.TestCase):
    """Test thread safety of managers."""
    
    def setUp(self):
        """Set up test fixture."""
        self.manager = DocumentManager()
        self.doc_id = 'thread-safe-1'
        self.doc = self.manager.get_or_create(self.doc_id)
    
    def test_concurrent_updates(self):
        """Test concurrent document updates."""
        def update_doc(user_id, count):
            for i in range(count):
                self.doc.update(f'Edit by {user_id} #{i}', user_id, 
                              f'edit-{user_id}-{i}', time.time() + i)
        
        threads = [
            threading.Thread(target=update_doc, args=('user-1', 5)),
            threading.Thread(target=update_doc, args=('user-2', 5)),
            threading.Thread(target=update_doc, args=('user-3', 5))
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Final version should be 15 (3 users × 5 edits)
        self.assertEqual(self.doc.version, 15)


class TestConflictDetectionScenarios(unittest.TestCase):
    """Test various conflict detection scenarios."""
    
    def setUp(self):
        """Set up test fixture."""
        self.detector = ConflictDetector()
    
    def test_conflict_multiline_edit(self):
        """Test conflict detection with multiline edits."""
        now = time.time()
        
        original = "line 1\nline 2\nline 3"
        edit1 = "line 1\nline 2 modified\nline 3"
        edit2 = "line 1\nline 2 different\nline 3"
        
        # User 1 edits line 2
        self.detector.detect_conflict('doc-1', now, 'user-1', edit1, original)
        
        # User 2 edits line 2 at almost same time
        is_conflict, lines = self.detector.detect_conflict(
            'doc-1', now + 0.3, 'user-2', edit2, original
        )
        
        self.assertTrue(is_conflict)
    
    def test_conflict_reset(self):
        """Test conflict state reset."""
        now = time.time()
        
        # First edit by user-1
        self.detector.detect_conflict('doc-1', now, 'user-1', 'content-1', '')
        
        # Reset conflict state
        self.detector.reset_for_doc('doc-1')
        
        # After reset, edit by user-2 should not conflict (no previous edit)
        is_conflict, _ = self.detector.detect_conflict(
            'doc-1', now + 0.5, 'user-2', 'content-2', ''
        )
        self.assertFalse(is_conflict)
def create_test_report(result):
    """Generate a test report."""
    report = {
        'timestamp': datetime.now().isoformat(),
        'total_tests': result.testsRun,
        'failures': len(result.failures),
        'errors': len(result.errors),
        'skipped': len(result.skipped),
        'success': result.wasSuccessful(),
        'success_rate': f"{((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%"
    }
    return report


if __name__ == '__main__':
    # Run tests with verbose output
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestDocument))
    suite.addTests(loader.loadTestsFromTestCase(TestDocumentManager))
    suite.addTests(loader.loadTestsFromTestCase(TestEditLogger))
    suite.addTests(loader.loadTestsFromTestCase(TestPresenceTracker))
    suite.addTests(loader.loadTestsFromTestCase(TestConflictDetector))
    suite.addTests(loader.loadTestsFromTestCase(TestRealTimeCollaboration))
    suite.addTests(loader.loadTestsFromTestCase(TestMultiDocumentBehavior))
    suite.addTests(loader.loadTestsFromTestCase(TestThreadSafety))
    suite.addTests(loader.loadTestsFromTestCase(TestConflictDetectionScenarios))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Generate report
    report = create_test_report(result)
    report_path = Path(__file__).parent / 'test_report.json'
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nTest Report saved to: {report_path}")
    print(f"Success Rate: {report['success_rate']}")
