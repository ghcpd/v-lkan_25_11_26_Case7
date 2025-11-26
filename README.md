# Lightweight Collaboration Platform

A real-time, browser-based collaborative document editor with conflict detection, presence awareness, and persistent edit logging — **no authentication required**.

## 🎯 Features

### Core Collaboration
- **Real-time Editing**: Multiple users edit the same document simultaneously via WebSockets
- **Anonymous Sessions**: No login needed; each user gets a temporary session ID (e.g., `user-abc123`)
- **Last-Write-Wins (LWW)**: Server accepts the most recent update as authoritative
- **Multi-Document Support**: Create and manage unlimited independent documents

### Persistence & History
- **Document Persistence**: All content stored as JSON files on disk
- **JSONL Edit Logs**: Append-only event logs for every edit (replay-able on startup)
- **Version Tracking**: Each document maintains version numbers and edit metadata

### Conflict Handling
- **Timestamp-Based Detection**: Conflicts detected when multiple users edit within 1 second
- **Line-Level Granularity**: Identifies which lines were affected by conflicting edits
- **Visual Feedback**: Highlighting and console warnings for conflicting changes
- **Client-Side Visualization**: Affected lines highlighted in real-time

### Presence & UI
- **Live User Count**: Displays how many users are currently editing
- **User List**: Shows all active users with live indicators
- **Edit History**: Displays recent edits with timestamps and user info
- **Status Bar**: Real-time sync status, edit counts, and version info

### Client Optimization
- **400ms Debounce**: Edit events batched to reduce server load
- **Incremental Updates**: Only changes are transmitted
- **Debug Console**: Built-in logging for troubleshooting

---

## 📋 Architecture

### Backend (Flask + Flask-SocketIO)
```
app.py
├── Document           # Document content + version management
├── DocumentManager    # Persistence layer for documents
├── EditLogger         # JSONL append-only event logs
├── PresenceTracker    # Real-time user presence tracking
├── ConflictDetector   # Timestamp + line-based conflict detection
└── WebSocket Routes   # connect, disconnect, join_document, edit, etc.
```

### Frontend (HTML5 + JavaScript)
```
templates/index.html  # Main UI
static/
├── client.js         # Collaboration logic, event handling, debouncing
└── style.css         # Responsive UI design
```

### Data Persistence
```
data/
├── documents/        # Document snapshots (doc_id.json)
└── logs/             # Edit event logs (doc_id.jsonl)
```

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.8+
- pip (Python package manager)
- Modern web browser (Chrome, Firefox, Safari, Edge)

### 2. Setup
```bash
# Clone or download the project
cd v-lkan_25_11_26_Case7

# Run setup script
bash setup.sh
# Or on Windows:
# python -m venv venv
# venv\Scripts\activate
# pip install -r requirements.txt

# Activate virtual environment
source venv/bin/activate
# On Windows: venv\Scripts\activate
```

### 3. Run the Server
```bash
python app.py
```
Server will start on `http://localhost:5000`

### 4. Open in Browser
- Visit: `http://localhost:5000`
- Multiple browser tabs or windows can connect to the same document
- Each connection gets a unique user ID
- Start typing and watch edits sync in real-time!

---

## 🧪 Testing

### Run Full Test Suite
```bash
bash run_test.sh
```

Or directly:
```bash
python test_suite.py
```

### Test Coverage
- ✅ Document creation, updates, serialization
- ✅ Persistence and replay from disk
- ✅ JSONL event logging
- ✅ Presence tracking (join/leave)
- ✅ Conflict detection scenarios
- ✅ Last-Write-Wins strategy
- ✅ Multi-document independence
- ✅ Thread safety under concurrent load
- ✅ Edit debouncing simulation

### Sample Test Output
```
test_document_creation ... ok
test_document_update ... ok
test_concurrent_updates ... ok
test_conflict_same_time_window ... ok
test_persistence_and_replay ... ok
...
======================================================================
Ran 45 tests in 2.341s
OK

Success Rate: 100.0%
```

---

## 🐳 Docker Deployment

### Build Image
```bash
docker build -t collab-platform:latest .
```

### Run Container
```bash
docker run -p 5000:5000 -v collab-data:/app/data collab-platform:latest
```

Visit: `http://localhost:5000`

---

## 📖 API Reference

### REST Endpoints

#### List Documents
```
GET /api/documents
Response: { "documents": [...] }
```

#### Create Document
```
POST /api/documents
Response: { "id": "abc123", "content": "", "version": 0 }
```

#### Get Document
```
GET /api/documents/<doc_id>
Response: { "id": "doc_id", "content": "...", "version": 5 }
```

### WebSocket Events

#### Client → Server

**connect**
```javascript
// Automatic, triggered on new connection
```

**join_document**
```javascript
socket.emit('join_document', {
  doc_id: 'abc123',
  user_id: 'user-xyz'
})
```

**edit**
```javascript
socket.emit('edit', {
  doc_id: 'abc123',
  user_id: 'user-xyz',
  content: 'full document content',
  timestamp: 1700000000.123,
  edit_id: 'user-xyz-1700000000123'
})
```

**request_history**
```javascript
socket.emit('request_history', { doc_id: 'abc123' })
```

#### Server → Client

**user_id**
```javascript
// Received on connection
{ user_id: 'user-abc123' }
```

**document_loaded**
```javascript
{
  doc_id: 'abc123',
  content: 'Document content...',
  version: 5
}
```

**document_updated**
```javascript
{
  doc_id: 'abc123',
  content: 'Updated content...',
  version: 6,
  user_id: 'user-xyz',
  timestamp: 1700000000.456,
  edit_id: 'user-xyz-1700000000456'
}
```

**presence_updated**
```javascript
{
  count: 3,
  users: ['user-abc', 'user-def', 'user-ghi']
}
```

**conflict_detected**
```javascript
{
  doc_id: 'abc123',
  timestamp: 1700000000.789,
  user_id: 'user-xyz',
  affected_lines: [5, 6, 7],
  version: 8
}
```

**history_loaded**
```javascript
{
  doc_id: 'abc123',
  history: [
    { timestamp: 1700000000.1, user_id: 'user-abc', version: 1, ... },
    { timestamp: 1700000000.2, user_id: 'user-def', version: 2, ... }
  ],
  edit_count: 2
}
```

---

## ⚙️ Configuration

### Server Settings (app.py)
```python
# Port
socketio.run(app, host='0.0.0.0', port=5000, debug=True)

# Conflict detection time window (seconds)
CONFLICT_TIME_WINDOW = 1.0

# Data directory
DATA_DIR = Path(__file__).parent / 'data'
```

### Client Settings (static/client.js)
```javascript
// Edit debounce delay (ms)
DEBOUNCE_DELAY = 400

// Conflict visualization timeout (ms)
conflictTimeout = 5000
```

---

## 📊 File Structure

```
v-lkan_25_11_26_Case7/
├── app.py                       # Flask server + WebSocket handlers
├── test_suite.py               # Comprehensive test suite (45+ tests)
├── requirements.txt             # Python dependencies
├── Dockerfile                  # Docker image definition
├── setup.sh                    # Setup script for Unix/Linux/macOS
├── run_test.sh                 # Test runner script
├── README.md                   # This file
├── templates/
│   └── index.html              # Main HTML template
├── static/
│   ├── client.js               # Frontend collaboration logic
│   └── style.css               # Responsive styling
└── data/                       # Created at runtime
    ├── documents/              # Document snapshots (JSON)
    └── logs/                   # Edit events (JSONL)
```

---

## 🔄 Data Formats

### Document Storage (documents/doc_id.json)
```json
{
  "id": "abc123",
  "content": "Full document content here...",
  "version": 5,
  "last_edit_time": 1700000000.123
}
```

### Edit Log (logs/doc_id.jsonl)
```jsonl
{"timestamp": 1700000000.1, "user_id": "user-abc", "edit_id": "abc-1", "version": 1, "content_length": 42, "event": "edit"}
{"timestamp": 1700000000.2, "user_id": "user-def", "edit_id": "def-2", "version": 2, "content_length": 55, "event": "edit"}
{"timestamp": 1700000000.3, "user_id": "user-abc", "edit_id": "abc-3", "version": 3, "content_length": 70, "event": "edit"}
```

---

## 🧩 Conflict Resolution Strategy

### Detection
1. Server tracks timestamp of last edit for each document
2. When new edit arrives within **1 second** from previous edit AND from different user
3. Server checks if edited lines overlap with previous edit's lines
4. If overlap detected → **CONFLICT** broadcast to all clients

### Resolution
- **Last-Write-Wins (LWW)**: More recent timestamp wins
- Document is updated with newer content
- Conflict event sent to all clients with affected line numbers
- Clients highlight conflicting lines for visual feedback

### Example
```
User A edits lines [2,3] at t=1000.0
User B edits lines [3,4] at t=1000.3
→ Conflict detected (overlap on line 3, within 1 second)
→ User B's edit wins (t=1000.3 > t=1000.0)
→ Both clients receive: conflict_detected event with affected_lines=[2,3,4]
```

---

## 🔍 Debugging

### Browser Console
All events logged to browser console:
```javascript
[INFO] User ID assigned: user-abc123
[INFO] Document loaded: doc-123
[INFO] WebSocket connected
[INFO] Document updated by user-def (v5)
[WARN] Conflict detected by user-ghi at lines: 5, 6, 7
[ERROR] Connection error: Network timeout
```

### Server Logs
```
2024-11-26 10:30:45,123 - app - INFO - Starting Lightweight Collaboration Platform...
2024-11-26 10:30:50,456 - app - INFO - Client connected: user-abc123 (sid: abc123def456)
2024-11-26 10:30:55,789 - app - INFO - user-abc123 joined document abc123. Presence: 1
2024-11-26 10:31:00,012 - app - INFO - user-abc123 edited abc123 (v1). Conflict: False
```

### Debug Console UI
Built-in console in bottom-right corner of web interface:
- Toggle with "–" button
- Shows all client-side events and errors
- Color-coded: green (info), yellow (warn), red (error)

---

## 📈 Performance Notes

- **Debounce Delay**: 400ms prevents server overload during rapid typing
- **WebSocket Binary**: Could be enabled for large documents
- **Client Caching**: Currently stateless; could add local drafts
- **Conflict Window**: 1 second is configurable; adjust for slower networks
- **JSONL Format**: Append-only; supports efficient replay and analytics

---

## 🔐 Security Considerations

⚠️ **This is a demo/educational platform. For production:**
- Add user authentication (OAuth2, JWT, etc.)
- Implement rate limiting
- Add HTTPS/WSS encryption
- Validate document access permissions
- Implement audit logging with user identification
- Add CSRF protection
- Sanitize content before storage

---

## 🐛 Known Limitations

1. **No conflict merge**: Uses simple LWW, not operational transformation
2. **No document metadata**: No titles, descriptions, or tags
3. **No authentication**: All documents are publicly readable
4. **No permissions**: No access control or sharing settings
5. **Single server**: No distribution or clustering
6. **Memory limits**: Edit history kept in memory (not persisted per-edit)

---

## 🚀 Future Enhancements

- [ ] User authentication & authorization
- [ ] Operational Transformation (OT) for better conflict resolution
- [ ] Rich text editor (Markdown, formatting)
- [ ] Document sharing & permissions
- [ ] Real-time cursor positions
- [ ] Comments & annotations
- [ ] Version snapshots & rollback
- [ ] Search across documents
- [ ] Collaborative cursors (showing where others are typing)
- [ ] Export to PDF/Word
- [ ] Offline support with sync

---

## 📝 Test Report Template

Generated by `run_test.sh`, saved as `test_report.json`:

```json
{
  "timestamp": "2024-11-26T10:30:45.123456",
  "total_tests": 45,
  "failures": 0,
  "errors": 0,
  "skipped": 0,
  "success": true,
  "success_rate": "100.0%"
}
```

---

## 📞 Support & Contributing

For issues, questions, or contributions:
1. Check existing test cases in `test_suite.py`
2. Review API documentation above
3. Check server/browser logs for errors
4. Verify setup with `python test_suite.py`

---

## 📄 License

Educational/Demo project - MIT License

---

**Happy Collaborating! 🎉**