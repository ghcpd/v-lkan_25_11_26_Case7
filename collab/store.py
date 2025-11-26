import json
import os
import time
import threading
from typing import Dict, List, Optional, Tuple


def compute_changed_lines(old: str, new: str) -> List[int]:
    """
    Compute line indices that changed between old and new content.
    Returns a list of indices covering the minimal differing span.
    """
    old_lines = old.splitlines()
    new_lines = new.splitlines()
    max_len = max(len(old_lines), len(new_lines))
    start = 0
    while start < max_len:
        o = old_lines[start] if start < len(old_lines) else None
        n = new_lines[start] if start < len(new_lines) else None
        if o != n:
            break
        start += 1
    else:
        # contents identical
        return []

    end_old = len(old_lines) - 1
    end_new = len(new_lines) - 1
    while end_old >= start or end_new >= start:
        o = old_lines[end_old] if end_old >= start else None
        n = new_lines[end_new] if end_new >= start else None
        if o != n:
            break
        end_old -= 1
        end_new -= 1

    end = max(end_old, end_new)
    return list(range(start, end + 1))


class DocumentStore:
    def __init__(self, data_dir: str = "data", logs_subdir: str = "logs", state_subdir: str = "state"):
        self.data_dir = data_dir
        self.logs_dir = os.path.join(data_dir, logs_subdir)
        self.state_dir = os.path.join(data_dir, state_subdir)
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.state_dir, exist_ok=True)

        # in-memory structures
        # doc_id -> {"content": str, "version": int, "last_edits": {line_idx: {"timestamp": float, "user_id": str}}, "recent_edits": [ {"lines": set, "timestamp": float, "user_id": str} ]}
        self.docs: Dict[str, Dict] = {}
        self.lock = threading.Lock()

    def list_documents(self) -> List[str]:
        """Return list of known document IDs."""
        ids = set()
        for fname in os.listdir(self.logs_dir):
            if fname.endswith('.jsonl'):
                ids.add(fname[:-6])
        for fname in os.listdir(self.state_dir):
            if fname.endswith('.txt'):
                ids.add(fname[:-4])
        ids.update(self.docs.keys())
        return sorted(ids)

    def load_all(self):
        """Rebuild documents from logs; also load state snapshots if logs absent."""
        for doc_id in self.list_documents():
            self._load_document(doc_id)

    def _load_document(self, doc_id: str):
        self.docs[doc_id] = {
            "content": "",
            "version": 0,
            "last_edits": {},
            "recent_edits": [],
        }
        log_path = self._log_path(doc_id)
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    content = entry.get("content", "")
                    version = entry.get("version", 0)
                    changed_lines = entry.get("changed_lines", [])
                    user_id = entry.get("user_id", "unknown")
                    ts = entry.get("timestamp", time.time())
                    self._apply_loaded(doc_id, content, version, changed_lines, user_id, ts)
        else:
            # fallback to state snapshot
            state_path = self._state_path(doc_id)
            if os.path.exists(state_path):
                with open(state_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.docs[doc_id]["content"] = content
                self.docs[doc_id]["version"] = 1  # snapshot without history

    def _apply_loaded(self, doc_id: str, content: str, version: int, changed_lines: List[int], user_id: str, timestamp: float):
        doc = self.docs[doc_id]
        doc["content"] = content
        doc["version"] = max(doc.get("version", 0), version)
        for li in changed_lines:
            doc["last_edits"][li] = {"timestamp": timestamp, "user_id": user_id}
        doc["recent_edits"].append({"lines": set(changed_lines), "timestamp": timestamp, "user_id": user_id})

    def get_or_create(self, doc_id: str) -> Dict:
        if doc_id not in self.docs:
            self.docs[doc_id] = {
                "content": "",
                "version": 0,
                "last_edits": {},
                "recent_edits": [],
            }
        return self.docs[doc_id]

    def get_content(self, doc_id: str) -> Tuple[str, int]:
        with self.lock:
            doc = self.get_or_create(doc_id)
            return doc["content"], doc["version"]

    def apply_edit(self, doc_id: str, user_id: str, new_content: str, timestamp: Optional[float] = None) -> Tuple[int, List[int], Dict]:
        """
        Apply edit with LWW. Returns (version, changed_lines, conflict_info)
        conflict_info: {"has_conflict": bool, "conflicts": [...], "lines": list}
        """
        if timestamp is None:
            timestamp = time.time()
        with self.lock:
            doc = self.get_or_create(doc_id)
            old_content = doc["content"]
            changed_lines = compute_changed_lines(old_content, new_content)
            version = doc["version"] + 1
            doc["content"] = new_content
            doc["version"] = version

            # update last edits
            for li in changed_lines:
                doc["last_edits"][li] = {"timestamp": timestamp, "user_id": user_id}

            # detect conflicts
            conflict_info = self._detect_conflicts(doc_id, user_id, changed_lines, timestamp)

            # record recent edits (keep short window ~10 seconds to limit memory)
            doc["recent_edits"].append({"lines": set(changed_lines), "timestamp": timestamp, "user_id": user_id})
            cutoff = timestamp - 10.0
            doc["recent_edits"] = [e for e in doc["recent_edits"] if e["timestamp"] >= cutoff]

            # persist
            self._append_log(doc_id, {
                "timestamp": timestamp,
                "user_id": user_id,
                "doc_id": doc_id,
                "version": version,
                "content": new_content,
                "changed_lines": changed_lines,
            })
            self._write_state(doc_id, new_content)
            return version, changed_lines, conflict_info

    def _detect_conflicts(self, doc_id: str, user_id: str, changed_lines: List[int], timestamp: float, window: float = 2.0) -> Dict:
        doc = self.docs[doc_id]
        conflicts = []
        lines_set = set(changed_lines)
        if not lines_set:
            return {"has_conflict": False, "conflicts": [], "lines": []}
        # check recent edits by other users within window
        for e in doc.get("recent_edits", []):
            if e["user_id"] == user_id:
                continue
            if timestamp - e["timestamp"] > window:
                continue
            # overlap or adjacency
            prev_lines = e["lines"]
            if self._overlap_or_adjacent(lines_set, prev_lines):
                conflicts.append({
                    "user_id": e["user_id"],
                    "timestamp": e["timestamp"],
                    "lines": sorted(list(prev_lines)),
                })
        all_conflict_lines = sorted(list(lines_set)) if conflicts else []
        return {"has_conflict": bool(conflicts), "conflicts": conflicts, "lines": all_conflict_lines}

    @staticmethod
    def _overlap_or_adjacent(lines_a: set, lines_b: set) -> bool:
        if not lines_a or not lines_b:
            return False
        # overlap
        if lines_a.intersection(lines_b):
            return True
        # adjacency
        for la in lines_a:
            if (la - 1) in lines_b or (la + 1) in lines_b:
                return True
        return False

    def _append_log(self, doc_id: str, entry: Dict):
        path = self._log_path(doc_id)
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _write_state(self, doc_id: str, content: str):
        path = self._state_path(doc_id)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    def _log_path(self, doc_id: str) -> str:
        return os.path.join(self.logs_dir, f"{doc_id}.jsonl")

    def _state_path(self, doc_id: str) -> str:
        return os.path.join(self.state_dir, f"{doc_id}.txt")
