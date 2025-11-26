Mini Collab Editor

Features:
- Real-time collaborative editing via Flask-SocketIO (WebSockets)
- Simple LWW (Last Write Wins) conflict resolution
- Presence awareness with temporary anonymous user IDs
- Edit debouncing implemented on client (400 ms)
- Persistent JSONL logs per document (replay on startup)
- Conflict detection for overlapping/adjacent lines within a short time window

Quickstart:
- Windows: run `setup.sh` to install dependencies
- Run server: `python app.py`
- Open http://localhost:5000 in your browser

Testing:
- Run tests: `run_test.sh` (bash) or `pytest -q` on Windows

Logs and persistence:
- Document logs are stored in `logs/<doc_id>.jsonl` as append-only JSON lines

