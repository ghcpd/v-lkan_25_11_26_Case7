# Collaborative Lightweight Editor

## Feature Highlights
- **Real-time multi-user editing** via Flask-SocketIO (WebSockets)
- **Last-Write-Wins (LWW)** concurrency strategy
- **Anonymous presence awareness**: auto-assigned `user-xxxx` IDs, live user counts
- **Client-side 400 ms debounce** to reduce chatter
- **Persistent storage**: JSONL append-only logs + state snapshots; state rebuilt at startup
- **Conflict visualization**: overlapping/adjacent line edits within ~2 s trigger conflict events; client highlights and logs
- **Multi-document support**: each document is an independent session

## Quickstart (Windows)
```powershell
Set-Location D:\Downloads\raptor-secondary\v-lkan_25_11_26_Case7
"D:\package\venv310\Scripts\python.exe" -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python app.py
```

## Quickstart (macOS/Linux)
```bash
cd /path/to/v-lkan_25_11_26_Case7
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

App runs on http://localhost:5000. Create/join docs via the UI.

## Running Tests
- One-click scripts: `run_test.bat` (Windows) or `run_test.sh` (bash)
- Manual: `.\.venv\Scripts\python -m pytest -vv --maxfail=1` (Windows) or `python -m pytest -vv --maxfail=1` (POSIX)

## Docker
```bash
docker build -t collab .
docker run --rm -p 5000:5000 -v $PWD/data:/data collab
```

## Persistence Layout
- Logs: `data/logs/<doc_id>.jsonl` (append-only edits)
- Snapshots: `data/state/<doc_id>.txt`
- On startup, logs are replayed to reconstruct content/version; snapshots are fallback.

## Conflict Detection (Simulation)
- Server watches recent edits (~10 s) and flags conflicts when another user edits overlapping/adjacent lines within ~2 s.
- Emits `conflict` events with affected lines and users; client shows banner and highlight.

## File Map
- `app.py` – entrypoint
- `collab/server.py` – Flask/SocketIO endpoints, presence, LWW
- `collab/store.py` – persistence, conflict detection, replay
- `templates/index.html`, `templates/doc.html` – UI
- `static/client.js`, `static/style.css` – client logic & styling
- `tests/` – pytest suite for collaboration, persistence, conflicts, multi-doc isolation
- `Dockerfile`, `requirements.txt`, `run_test.*`, `setup.sh`, `test_report_template.md`

## Test Report Template
Fill `test_report_template.md` with run metadata, pass/fail summary, and notable observations.

## Notes
- Tested with Python 3.10.17 on Windows. Eventlet warnings about distutils are benign.