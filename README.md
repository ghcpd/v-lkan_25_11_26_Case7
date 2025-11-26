# Lightweight Collaboration — demo project

This repository implements a small, self-contained real-time collaborative editor (Flask + Socket.IO) with:

- Real-time editing via WebSockets (Flask-SocketIO)
- Simple Last-Write-Wins concurrency model
- Anonymous temporary session IDs (no authentication required)
- Presence counts for documents
- Client-side 400ms debounce to batch edits
- Persistent storage and append-only JSONL edit logs
- Conflict detection simulation (timestamp + line indices) and visual highlighting
- Reproducible run / test scripts + Dockerfile and pytest-based tests

This project is intentionally minimal and focused on the features requested in the assignment.

Quick start
-----------

Requirements

- Python 3.10+ recommended
- The project requirements are in `requirements.txt`.

Run locally (dev)

1. Install dependencies (optional):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the server:

```bash
python app.py
# or
./run_server.sh
```

3. Open http://localhost:5000 in multiple browsers/tabs to try collaborative editing.

Files of interest
-----------------

- `app.py` — Flask + Flask-SocketIO server, DocumentStore and core logic (LWW, logging, conflict detection)
- `static/index.html`, `static/main.js` — simple web client demonstrating presence + debounced updates
- `data/` — persisted document contents (created at runtime)
- `logs/` — append-only JSONL logs for edits and conflict events
- `tests/` — pytest-based tests and report template

Testing and automation

Run the test suite with:

```bash
./run_test.sh
```
 
 Run tests (cmd.exe, Windows):
 ```cmd
 REM create venv with your chosen interpreter and run tests (example using your path)
 D:\package\venv310\Scripts\python.exe -m venv .venv
 .venv\Scripts\activate
 pip install -r requirements.txt
 pytest -q
 
 REM or use the convenience script bundled in the repo:
 run_test_windows.bat "D:\package\venv310\Scripts\python.exe"
 ```

This will execute the tests under `tests/` which cover:

- Persistence and replay of logs
- Conflict detection logic
- Basic real-time roundtrip (in-process SocketIO test clients)
- Multi-document isolation

Docker
------

Build the image and run in a container:

```bash
docker build -t lightweight-collab .
docker run -p 5000:5000 lightweight-collab
```

Design notes (how requirements map)
----------------------------------

1. Real-time Collaboration
	- Implemented with Flask-SocketIO; multiple clients can join the same doc room and receive updates.

2. Concurrency Handling (LWW)
	- Server applies incoming updates as authoritative (LWW) and broadcasts the resulting state to all clients.

3. User Presence Awareness
	- Temporary session IDs are assigned on connect; presence counts are tracked per-document and broadcast.

4. Edit Debouncing
	- Client applies a 400ms debounce before sending updates (see `static/main.js`).

5. Persistence & Edit Logging
	- Each edit is appended as a JSONL record in `logs/<doc_id>.jsonl` and the authoritative content is stored in `data/<doc_id>.txt`.
	- On startup the server rebuilds documents by replaying logs.

6. Conflict Visualization
	- The server detects conflicts using timestamp + affected line indices and broadcasts a `conflict` event.
	- Client highlights conflicting lines in the UI (red background) — this is a visual simulation rather than a merge.

7. Anonymous User Identification
	- No authentication — each socket connection is assigned a `user-<hex>` ID and stored per-connection.

Anything else?
---------------

CI
--
I added a GitHub Actions workflow at `.github/workflows/ci.yml` that runs the test suite on push and PR for Python 3.10 and 3.11.

If you'd like, I can also:

- Harden tests further or add test matrix items (OS, python versions)
- Replace the contentEditable UI with CodeMirror/Monaco for better line-targeted editing
- Add an optional merge strategy or operational transforms for true CRDT/OT merging
