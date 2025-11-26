# Collaborative Document Editor

A real-time collaborative document editing system built with Flask-SocketIO, featuring conflict detection, persistent storage, and anonymous user sessions.

## Features

✨ **Real-time Collaboration**
- Multiple users can edit the same document simultaneously
- WebSocket-based live updates (Flask-SocketIO)
- Changes propagate instantly to all connected clients

👥 **Anonymous User Sessions**
- No login required
- Automatic temporary user ID assignment (e.g., `user-abc123`)
- User presence awareness showing active editors

⚡ **Optimized Performance**
- 400ms client-side debouncing to prevent excessive events
- Efficient batching of continuous typing
- Minimal server load

🔄 **Conflict Detection & Visualization**
- Server-side detection of concurrent edits
- Highlights conflicting text sections
- Console warnings for debugging
- Last-Write-Wins (LWW) resolution strategy

💾 **Persistent Storage**
- Document state stored on disk
- Append-only JSONL edit logs
- Automatic recovery on server restart
- Complete version history

📊 **Version History**
- Every edit logged with timestamp and user
- Retrievable edit history
- Version numbering

## Architecture

```
├── app.py                  # Flask-SocketIO backend server
├── templates/
│   ├── index.html          # Home page (create/open documents)
│   └── editor.html         # Collaborative editor interface
├── data/
│   └── logs/               # JSONL edit logs (auto-generated)
│       └── {doc_id}.jsonl  # Per-document edit history
├── test_collaboration.py   # Comprehensive test suite
├── requirements.txt        # Python dependencies
├── Dockerfile              # Container configuration
├── setup.sh / setup.bat    # Environment setup scripts
└── run_test.sh / .bat      # Automated test runners
```

## Quick Start

### Option 1: Local Setup (Windows)

```cmd
# Run setup script
setup.bat

# Activate virtual environment
venv\Scripts\activate

# Start the server
python app.py

# Open browser to http://localhost:5000
```

### Option 2: Local Setup (Linux/Mac)

```bash
# Make scripts executable
chmod +x setup.sh run_test.sh

# Run setup
./setup.sh

# Activate virtual environment
source venv/bin/activate

# Start the server
python app.py

# Open browser to http://localhost:5000
```

### Option 3: Docker

```bash
# Build image
docker build -t collab-editor .

# Run container
docker run -p 5000:5000 -v $(pwd)/data:/app/data collab-editor

# Open browser to http://localhost:5000
```

## Usage

### Creating a Document

1. Visit `http://localhost:5000`
2. Click "Create New Document"
3. Share the document URL with collaborators

### Opening an Existing Document

1. Visit `http://localhost:5000`
2. Enter document ID
3. Click "Open"

### Collaborating

- Multiple users can open the same document URL
- Changes appear in real-time for all users
- User count shows active editors
- Conflicts are automatically detected and highlighted

## Testing

### Run All Tests

**Windows:**
```cmd
run_test.bat
```

**Linux/Mac:**
```bash
./run_test.sh
```

### Run Specific Tests

```bash
# Activate virtual environment first
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Run specific test class
pytest test_collaboration.py::TestRealtimeCollaboration -v

# Run specific test
pytest test_collaboration.py::TestRealtimeCollaboration::test_multi_user_collaboration -v
```

### Test Coverage

The test suite covers:

- ✅ Document creation and retrieval
- ✅ Real-time multi-user collaboration
- ✅ User presence tracking
- ✅ Edit logging and persistence
- ✅ Document recovery from logs
- ✅ Version incrementing
- ✅ Conflict detection
- ✅ Last-Write-Wins strategy
- ✅ Multi-document support
- ✅ Version history retrieval

### Test Reports

After running tests, reports are generated in `test_reports/`:

- `test_report_<timestamp>.txt` - Detailed text output
- `test_summary_<timestamp>.html` - Visual HTML summary

## API Reference

### REST Endpoints

**Create Document**
```http
POST /api/documents
Response: {"doc_id": "abc123", "content": "", "version": 0}
```

**Get Document**
```http
GET /api/documents/{doc_id}
Response: {"doc_id": "abc123", "content": "...", "version": 5, "user_count": 2}
```

### WebSocket Events

**Client → Server**

```javascript
// Join document
socket.emit('join_document', {doc_id: 'abc123'});

// Edit document
socket.emit('edit_document', {
    content: 'Updated content',
    cursor_position: 42
});

// Request history
socket.emit('request_history', {doc_id: 'abc123'});
```

**Server → Client**

```javascript
// User assigned
socket.on('user_assigned', (data) => {
    // data: {user_id: 'user-abc123'}
});

// Document state
socket.on('document_state', (data) => {
    // data: {content: '...', version: 5, user_count: 2}
});

// Document updated
socket.on('document_updated', (data) => {
    // data: {content: '...', version: 6, user_id: 'user-xyz'}
});

// Conflict detected
socket.on('conflict_detected', (data) => {
    // data: {detected: true, current_user: '...', conflicts: [...]}
});

// User joined/left
socket.on('user_joined', (data) => {
    // data: {user_id: 'user-def456', user_count: 3}
});

// History response
socket.on('history_response', (data) => {
    // data: {history: [{user_id, version, timestamp, preview}, ...]}
});
```

## Configuration

### Server Settings

Edit `app.py`:

```python
# Server port
socketio.run(app, host='0.0.0.0', port=5000)

# CORS settings
CORS(app, origins=['http://localhost:3000'])

# Data directory
DATA_DIR = 'data'
```

### Client Settings

Edit `templates/editor.html`:

```javascript
// Debounce delay (milliseconds)
debounceTimer = setTimeout(() => {
    // Send update
}, 400);  // Adjust this value
```

## Conflict Detection Algorithm

1. Track recent edits (last 10) per document
2. Calculate affected line ranges for each edit
3. On new edit, check for:
   - Different user
   - Within 2-second window
   - Overlapping or adjacent lines
4. If conflict detected:
   - Broadcast conflict event to all clients
   - Apply Last-Write-Wins strategy
   - Highlight conflicting sections

## Persistence Format

Each document has a JSONL log file: `data/logs/{doc_id}.jsonl`

**Create Event:**
```json
{"action": "create", "doc_id": "abc123", "timestamp": "2025-11-26T10:00:00"}
```

**Edit Event:**
```json
{
    "action": "edit",
    "doc_id": "abc123",
    "user_id": "user-xyz",
    "content": "Document content",
    "version": 5,
    "timestamp": "2025-11-26T10:05:30",
    "metadata": {"cursor_position": 42}
}
```

## Troubleshooting

### Port Already in Use

```bash
# Find process on port 5000
# Windows
netstat -ano | findstr :5000
taskkill /PID <pid> /F

# Linux/Mac
lsof -ti:5000 | xargs kill -9
```

### WebSocket Connection Failed

- Check firewall settings
- Verify CORS configuration
- Ensure server is running on correct port

### Tests Failing

```bash
# Clean data directory
rm -rf data/logs/*  # Linux/Mac
rmdir /s /q data\logs  # Windows

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## Performance Considerations

- **Debouncing:** 400ms delay reduces events by ~90%
- **Log Rotation:** Consider archiving old logs for long-running documents
- **Scalability:** Current implementation is single-server; use Redis for multi-server setups
- **Conflict Window:** 2-second window balances detection vs false positives

## Future Enhancements

- [ ] Rich text editing (Quill/ProseMirror)
- [ ] Operational Transformation (OT) for precise conflict resolution
- [ ] Redis-backed storage for horizontal scaling
- [ ] User authentication and permissions
- [ ] Document snapshots at intervals
- [ ] Export to PDF/Markdown
- [ ] Cursor position sharing
- [ ] Undo/redo support

## License

MIT License - Feel free to use and modify for your projects.

## Contributing

Contributions welcome! Please ensure:

1. All tests pass: `pytest test_collaboration.py`
2. Code follows existing style
3. New features include tests
4. Update documentation

## Support

For issues or questions:

1. Check the troubleshooting section
2. Review test cases for usage examples
3. Examine browser console for WebSocket errors
4. Check server logs for backend issues

---

**Built with Flask-SocketIO | Real-time | Persistent | Conflict-Aware**
