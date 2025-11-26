import os
import json
import time
import threading
from collections import defaultdict

LOGS_DIR = os.path.join(os.path.dirname(__file__), 'logs')
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

_lock = threading.Lock()

class Document:
    def __init__(self, doc_id):
        self.id = doc_id
        self.content = ""
        self.last_edit_ts = 0.0
        self.edits = []
        self.log_path = os.path.join(LOGS_DIR, f"{doc_id}.jsonl")
        self._load_from_log()

    def _load_from_log(self):
        # Rebuild document by sequentially applying logged edits
        if not os.path.exists(self.log_path):
            return
        with open(self.log_path, 'r', encoding='utf-8') as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                    # Only 'edit' records contain 'content'
                    if rec.get('action') == 'create' and 'content' in rec:
                        self.content = rec['content']
                        self.last_edit_ts = rec.get('ts', 0.0)
                        self.edits.append(rec)
                    elif rec.get('action') == 'edit' and 'content' in rec:
                        # Apply content update
                        self.content = rec['content']
                        self.last_edit_ts = rec.get('ts', 0.0)
                        self.edits.append(rec)
                    else:
                        # store other events for history
                        self.edits.append(rec)
                except json.JSONDecodeError:
                    continue

    def append_log(self, record):
        with _lock:
            with open(self.log_path, 'a', encoding='utf-8') as fh:
                fh.write(json.dumps(record) + "\n")
            self.edits.append(record)
            # apply LWW by timestamp
            if record.get('action') in ('create', 'edit') and record.get('ts', 0) >= self.last_edit_ts:
                self.content = record.get('content', self.content)
                self.last_edit_ts = record.get('ts', self.last_edit_ts)

class CollabManager:
    def __init__(self):
        self.docs = {}
        self.presence = defaultdict(set)  # doc_id -> set(user_id)
        self.user_sessions = {}  # sid->user_id
        self.load_all_docs()

    def load_all_docs(self):
        # find any logs present in LOGS_DIR
        for fname in os.listdir(LOGS_DIR):
            if fname.endswith('.jsonl'):
                doc_id = fname[:-6]
                try:
                    self.docs[doc_id] = Document(doc_id)
                except Exception:
                    pass

    def create_doc(self, doc_id, initial_content, user_id):
        if doc_id in self.docs:
            return False
        doc = Document(doc_id)
        create_record = {
            'action': 'create',
            'doc_id': doc_id,
            'user_id': user_id,
            'ts': time.time(),
            'content': initial_content,
        }
        doc.append_log(create_record)
        self.docs[doc_id] = doc
        return True

    def get_doc(self, doc_id):
        return self.docs.get(doc_id)

    def apply_edit(self, doc_id, content, user_id, ts, start_line=None, end_line=None):
        doc = self.get_doc(doc_id)
        if not doc:
            return None
        rec = {
            'action': 'edit',
            'doc_id': doc_id,
            'user_id': user_id,
            'ts': ts,
            'content': content,
            'start_line': start_line,
            'end_line': end_line,
        }
        doc.append_log(rec)
        return rec

    def add_presence(self, doc_id, user_id):
        self.presence[doc_id].add(user_id)

    def remove_presence(self, doc_id, user_id):
        self.presence[doc_id].discard(user_id)

    def get_presence_count(self, doc_id):
        return len(self.presence[doc_id])

    def list_docs(self):
        return list(self.docs.keys())

    def detect_conflict(self, doc_id, user_id, ts, start_line, end_line, window_seconds=2.0):
        doc = self.get_doc(doc_id)
        if not doc:
            return False, []
        conflicts = []
        # Look for edits in doc.edits within window_seconds that overlap lines
        for rec in reversed(doc.edits[-50:]):
            if rec.get('action') != 'edit':
                continue
            if rec.get('user_id') == user_id:
                continue
            prev_ts = rec.get('ts', 0)
            if abs(ts - prev_ts) > window_seconds:
                continue
            prev_start = rec.get('start_line')
            prev_end = rec.get('end_line')
            if prev_start is None or prev_end is None or start_line is None or end_line is None:
                continue
            # conflict if ranges overlap or adjacent
            if not (end_line < prev_start - 1 or start_line > prev_end + 1):
                conflicts.append(rec)
        return (len(conflicts) > 0), conflicts

manager = CollabManager()
