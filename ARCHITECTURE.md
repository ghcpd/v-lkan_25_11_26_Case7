# ARCHITECTURE DIAGRAM

## System Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│                     LIGHTWEIGHT COLLABORATION PLATFORM             │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                    WEB BROWSER (CLIENT)                     │  │
│  │                                                             │  │
│  │  ┌────────────────────────────────────────────────────┐    │  │
│  │  │  HTML5 UI (templates/index.html)                  │    │  │
│  │  │  ┌──────────────────────────────────────────────┐ │    │  │
│  │  │  │ Header: Doc ID Input | User Info | Version  │ │    │  │
│  │  │  └──────────────────────────────────────────────┘ │    │  │
│  │  │  ┌──────────────────────────────────────────────┐ │    │  │
│  │  │  │          Main Editor (textarea)              │ │    │  │
│  │  │  │  ┌────────────────────────────────────────┐ │ │    │  │
│  │  │  │  │  Real-time text input area             │ │ │    │  │
│  │  │  │  │  - 400ms debounce (client.js)          │ │ │    │  │
│  │  │  │  │  - Conflict highlighting               │ │ │    │  │
│  │  │  │  └────────────────────────────────────────┘ │ │    │  │
│  │  │  └──────────────────────────────────────────────┘ │    │  │
│  │  │  ┌──────────────────────────────────────────────┐ │    │  │
│  │  │  │ Sidebar: Presence + History + Debug Console │ │    │  │
│  │  │  │ ┌──────────────────────────────────────────┐│ │    │  │
│  │  │  │ │ Active Users (with green indicator dots) ││ │    │  │
│  │  │  │ └──────────────────────────────────────────┘│ │    │  │
│  │  │  │ ┌──────────────────────────────────────────┐│ │    │  │
│  │  │  │ │ Edit History (last 5 edits)              ││ │    │  │
│  │  │  │ └──────────────────────────────────────────┘│ │    │  │
│  │  │  └──────────────────────────────────────────────┘ │    │  │
│  │  │  ┌──────────────────────────────────────────────┐ │    │  │
│  │  │  │ Conflict Panel (shows affected lines)        │ │    │  │
│  │  │  └──────────────────────────────────────────────┘ │    │  │
│  │  │  ┌──────────────────────────────────────────────┐ │    │  │
│  │  │  │ Debug Console (event logs, bottom-right)     │ │    │  │
│  │  │  └──────────────────────────────────────────────┘ │    │  │
│  │  └────────────────────────────────────────────────────┘    │  │
│  │                                                             │  │
│  │  CSS Styling (static/style.css) - Responsive, mobile-first│  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  JavaScript Client (static/client.js)                             │
│  ├─ CollaborationClient class                                     │
│  ├─ WebSocket event handling                                      │
│  ├─ Edit debouncing (400ms)                                       │
│  ├─ Conflict visualization                                        │
│  └─ Debug console management                                      │
│                                                                    │
│                       WebSocket (Socket.IO)                       │
│                          ↕ ↕ ↕ ↕                                   │
│                     http://localhost:5000                         │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
                                ↓
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│                  FLASK SERVER (Backend - app.py)                  │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │            CORE CLASSES & MANAGERS                           │ │
│  │                                                              │ │
│  │  ┌─────────────────────────────────────────────────────┐   │ │
│  │  │ Document Class                                      │   │ │
│  │  ├─ doc_id: string                                     │   │ │
│  │  ├─ content: string (full document text)              │   │ │
│  │  ├─ version: int (incremented per edit)               │   │ │
│  │  ├─ last_edit_time: timestamp                         │   │ │
│  │  ├─ edit_history: list of edits                       │   │ │
│  │  └─ update(new_content, user_id, edit_id, timestamp)  │   │ │
│  │  └─ to_dict() → JSON serialization                    │   │ │
│  │  └─ Thread-safe with self.lock                        │   │ │
│  │  └─ Last-Write-Wins applied here                      │   │ │
│  │  └─ Triggers: document_updated broadcast              │   │ │
│  │  └─ Triggers: JSONL log write                         │   │ │
│  │  └─ Triggers: JSON snapshot save                      │   │ │
│  │  └─ Triggers: conflict_detected event                 │   │ │
│  │  └─ Triggers: presence_updated broadcast              │   │ │
│  │  └─ Triggers: version increment                       │   │ │
│  │  └─ Max version = number of total edits               │   │ │
│  └─────────────────────────────────────────────────────────┘   │ │
│  │                                                              │ │
│  │  ┌─────────────────────────────────────────────────────┐   │ │
│  │  │ DocumentManager Class                               │   │ │
│  │  ├─ documents: dict[doc_id → Document]                │   │ │
│  │  ├─ lock: threading.Lock                              │   │ │
│  │  ├─ get_or_create(doc_id) → Document                 │   │ │
│  │  │  ├─ Load from disk if exists                       │   │ │
│  │  │  └─ Create new if doesn't exist                    │   │ │
│  │  ├─ save_document(doc_id)                             │   │ │
│  │  │  └─ Write to data/documents/doc_id.json            │   │ │
│  │  ├─ _load_all_documents()                             │   │ │
│  │  │  └─ Startup: load all docs from disk               │   │ │
│  │  └─ Thread-safe with self.lock                        │   │ │
│  │                                                         │   │ │
│  │  Thread Safety: All write ops acquire lock first       │   │ │
│  │  Startup Behavior: Loads all docs from disk            │   │ │
│  │  Data Consistency: Writes to both JSON + JSONL         │   │ │
│  └─────────────────────────────────────────────────────────┘   │ │
│  │                                                              │ │
│  │  ┌─────────────────────────────────────────────────────┐   │ │
│  │  │ EditLogger Class                                     │   │ │
│  │  ├─ log_edit(doc_id, user_id, edit_id,                │   │ │
│  │  │           content, timestamp, version)             │   │ │
│  │  │  └─ Append to data/logs/doc_id.jsonl               │   │ │
│  │  │  └─ One JSON object per line (JSONL format)        │   │ │
│  │  │  └─ Never overwrites, always appends               │   │ │
│  │  └─ Thread-safe append with self.lock                 │   │ │
│  │                                                         │   │ │
│  │  Audit Trail: Complete edit history (replay-able)      │   │ │
│  │  Performance: O(1) append operation                     │   │ │
│  │  Storage: Minimal (just metadata, not full content)    │   │ │
│  │  Recovery: Can replay to reconstruct state             │   │ │
│  └─────────────────────────────────────────────────────────┘   │ │
│  │                                                              │ │
│  │  ┌─────────────────────────────────────────────────────┐   │ │
│  │  │ PresenceTracker Class                               │   │ │
│  │  ├─ users_per_doc: dict[doc_id → set of user_ids]    │   │ │
│  │  ├─ session_to_user: dict[session_id → (doc_id,      │   │ │
│  │  │                      user_id)]                      │   │ │
│  │  ├─ join(doc_id, session_id, user_id)                │   │ │
│  │  │  └─ Add user to document's active set              │   │ │
│  │  ├─ leave(session_id)                                │   │ │
│  │  │  └─ Remove user from document                      │   │ │
│  │  ├─ get_presence(doc_id)                             │   │ │
│  │  │  └─ Return {count, users} for document             │   │ │
│  │  └─ Thread-safe with self.lock                        │   │ │
│  │                                                         │   │ │
│  │  Real-time: Updates visible within ~100ms             │   │ │
│  │  Isolation: Per-document presence tracking             │   │ │
│  │  Broadcast: Presence events sent to all users          │   │ │
│  └─────────────────────────────────────────────────────────┘   │ │
│  │                                                              │ │
│  │  ┌─────────────────────────────────────────────────────┐   │ │
│  │  │ ConflictDetector Class                               │   │ │
│  │  ├─ last_edits: dict[doc_id → {timestamp, user_id,    │   │ │
│  │  │              lines}]                                 │   │ │
│  │  ├─ CONFLICT_TIME_WINDOW = 1.0 seconds                │   │ │
│  │  ├─ detect_conflict(doc_id, timestamp, user_id,       │   │ │
│  │  │                  new_content, prev_content)        │   │ │
│  │  │  ├─ Check: timestamp - last_timestamp < 1 sec?     │   │ │
│  │  │  ├─ Check: user_id ≠ last_user_id?                │   │ │
│  │  │  ├─ Calculate affected lines in both versions      │   │ │
│  │  │  ├─ Check: affected_lines overlap?                │   │ │
│  │  │  └─ Return: (is_conflict, affected_lines)          │   │ │
│  │  ├─ reset_for_doc(doc_id)                             │   │ │
│  │  │  └─ Clear conflict state                           │   │ │
│  │  └─ Thread-safe with self.lock                        │   │ │
│  │                                                         │   │ │
│  │  Detection: Timestamp + line-based                     │   │ │
│  │  Resolution: Conflict event broadcasted               │   │ │
│  │  Visualization: Client highlights affected lines      │   │ │
│  │  Window: 1 second (configurable)                      │   │ │
│  └─────────────────────────────────────────────────────────┘   │ │
│  │                                                              │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                  WEBSOCKET EVENT HANDLERS                    │ │
│  │                                                              │ │
│  │  @socketio.on('connect')                                    │ │
│  │  └─ Assign temporary user_id to client                     │ │
│  │  └─ Emit 'user_id' back to client                          │ │
│  │                                                              │ │
│  │  @socketio.on('join_document')                              │ │
│  │  ├─ Add user to room                                        │ │
│  │  ├─ Register in PresenceTracker                            │ │
│  │  ├─ Load document from DocumentManager                     │ │
│  │  ├─ Emit 'document_loaded' to client                       │ │
│  │  ├─ Broadcast 'presence_updated' to room                   │ │
│  │  └─ Log: user joined                                        │ │
│  │                                                              │ │
│  │  @socketio.on('edit')                                       │ │
│  │  ├─ Get document                                           │ │
│  │  ├─ Detect conflicts via ConflictDetector                 │ │
│  │  ├─ Apply Last-Write-Wins update                          │ │
│  │  ├─ Save document (DocumentManager)                       │ │
│  │  ├─ Log edit (EditLogger)                                 │ │
│  │  ├─ Broadcast 'document_updated' to room                  │ │
│  │  ├─ If conflict: broadcast 'conflict_detected'            │ │
│  │  └─ Log: edit made                                         │ │
│  │                                                              │ │
│  │  @socketio.on('request_history')                            │ │
│  │  ├─ Read JSONL log from disk                              │ │
│  │  ├─ Parse each line                                       │ │
│  │  ├─ Emit 'history_loaded' to client                       │ │
│  │  └─ Log: history requested                                │ │
│  │                                                              │ │
│  │  @socketio.on('disconnect')                                │ │
│  │  ├─ Remove user from PresenceTracker                      │ │
│  │  ├─ Broadcast 'presence_updated' to rooms                 │ │
│  │  └─ Log: user disconnected                                │ │
│  │                                                              │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                    REST API ENDPOINTS                        │ │
│  │                                                              │ │
│  │  GET /                                                      │ │
│  │  └─ Serve index.html (Flask's render_template)            │ │
│  │                                                              │ │
│  │  GET /api/documents                                         │ │
│  │  └─ Return: {documents: [doc1, doc2, ...]}                │ │
│  │  └─ Shows all documents in system                         │ │
│  │  └─ Data: id, content, version, edit_count               │ │
│  │                                                              │ │
│  │  POST /api/documents                                        │ │
│  │  └─ Create new document                                    │ │
│  │  └─ Return: {id, content: "", version: 0}                │ │
│  │  └─ Generate random 8-char ID                            │ │
│  │                                                              │ │
│  │  GET /api/documents/<doc_id>                                │ │
│  │  └─ Get specific document                                  │ │
│  │  └─ Return: {id, content, version, last_edit_time}       │ │
│  │                                                              │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
                                ↓
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│                    FILE SYSTEM PERSISTENCE                        │
│                                                                    │
│  data/documents/                  (JSON Snapshots)                │
│  ├─ abc123.json                                                   │
│  │  {                                                             │
│  │    "id": "abc123",                                             │
│  │    "content": "Full document text...",                         │
│  │    "version": 5,                                               │
│  │    "last_edit_time": 1700000000.123                            │
│  │  }                                                             │
│  │                                                                │
│  ├─ def456.json                                                   │
│  └─ ...                                                            │
│                                                                    │
│  data/logs/                       (JSONL Edit Logs)               │
│  ├─ abc123.jsonl (Append-only, never overwritten)               │
│  │  {"timestamp": 1700000000.1, "user_id": "user-a",             │
│  │   "edit_id": "a-1", "version": 1, "content_length": 42}      │
│  │  {"timestamp": 1700000000.2, "user_id": "user-b",             │
│  │   "edit_id": "b-2", "version": 2, "content_length": 55}      │
│  │  {"timestamp": 1700000000.3, "user_id": "user-a",             │
│  │   "edit_id": "a-3", "version": 3, "content_length": 70}      │
│  │                                                                │
│  ├─ def456.jsonl                                                  │
│  └─ ...                                                            │
│                                                                    │
│  Benefits of this design:                                         │
│  ✓ JSON snapshots: Fast current state retrieval                  │
│  ✓ JSONL logs: Append-only, no rewriting                         │
│  ✓ Replay-able: Can reconstruct any version                      │
│  ✓ Human-readable: Can inspect files directly                    │
│  ✓ Auditable: Complete edit history preserved                    │
│  ✓ No database: Simple file-based storage                        │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

## Communication Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│  User Typing Event                                       │
│  "H" → "He" → "Hel" → "Hell" → "Hello"                 │
└─────────────────────┬───────────────────────────────────┘
                      ↓
        ┌─────────────────────────────┐
        │ 400ms Debounce Timer        │
        │ (client.js)                 │
        │ ┌───────────────────────┐   │
        │ │ Reset on each keystroke   │
        │ │ Accumulate edits      │   │
        │ └───────────────────────┘   │
        └─────────────────────────────┘
                      ↓ (after 400ms of no typing)
        ┌─────────────────────────────┐
        │ emit('edit', {...})         │
        │ - doc_id                    │
        │ - user_id                   │
        │ - content (full document)   │
        │ - timestamp                 │
        │ - edit_id                   │
        └─────────────────────────────┘
                      ↓
        ┌─────────────────────────────┐
        │ WebSocket (SocketIO)        │
        │ HTTP/WebSocket Protocol     │
        └─────────────────────────────┘
                      ↓
        ┌─────────────────────────────┐
        │ Server: @socketio.on('edit')│
        │ ┌───────────────────────┐   │
        │ │ 1. Get document       │   │
        │ │ 2. Detect conflicts   │   │
        │ │ 3. Apply LWW          │   │
        │ │ 4. Save to disk       │   │
        │ │ 5. Log edit           │   │
        │ │ 6. Broadcast update   │   │
        │ │ 7. Broadcast conflict │   │
        │ └───────────────────────┘   │
        └─────────────────────────────┘
                      ↓
        ┌─────────────────────────────┐
        │ emit('document_updated', {})│
        │ - Broadcast to all clients  │
        │   in document room          │
        └─────────────────────────────┘
                      ↓
        ┌─────────────────────────────┐
        │ Client: socket.on(...)      │
        │ ┌───────────────────────┐   │
        │ │ 1. Update textarea    │   │
        │ │ 2. Update version     │   │
        │ │ 3. Show who edited    │   │
        │ │ 4. Update UI          │   │
        │ └───────────────────────┘   │
        └─────────────────────────────┘
                      ↓
        ┌─────────────────────────────┐
        │ User sees update instantly  │
        │ (on all connected clients)  │
        └─────────────────────────────┘
```

## Conflict Detection Flow

```
┌──────────────────────────────────────────────────┐
│ User A types at t=1000.0                         │
│ "line 2" → "line 2 modified by A"               │
│ Affected lines: [2]                              │
└──────────────────────┬───────────────────────────┘
                       ↓
        ┌──────────────────────────┐
        │ Server receives edit     │
        │ Store:                   │
        │  - timestamp: 1000.0     │
        │  - user_id: user-a       │
        │  - lines: [2]            │
        └──────────────────────────┘
                       ↓
        ┌──────────────────────────┐
        │ Update document          │
        │ Save to disk             │
        │ Log to JSONL             │
        └──────────────────────────┘


┌──────────────────────────────────────────────────┐
│ User B types at t=1000.3 (within conflict window)│
│ "line 2" → "line 2 modified by B"               │
│ Affected lines: [2]                              │
└──────────────────────┬───────────────────────────┘
                       ↓
        ┌──────────────────────────────────────┐
        │ ConflictDetector.detect_conflict()   │
        │ Check 1: 1000.3 - 1000.0 = 0.3s      │
        │          0.3s < 1.0s ? YES ✓         │
        │ Check 2: user-b ≠ user-a ? YES ✓    │
        │ Check 3: [2] & [2] = [2] ? YES ✓    │
        │ → CONFLICT DETECTED ✓                │
        └──────────────────────┬───────────────┘
                               ↓
        ┌──────────────────────────────────────┐
        │ Last-Write-Wins Applied              │
        │ Update document with user-b's version│
        │ (because 1000.3 > 1000.0)            │
        └──────────────────────┬───────────────┘
                               ↓
        ┌──────────────────────────────────────┐
        │ Broadcast to all clients:            │
        │ 'conflict_detected':                 │
        │ {                                    │
        │   "doc_id": "abc123",                │
        │   "timestamp": 1000.3,               │
        │   "user_id": "user-b",               │
        │   "affected_lines": [2],             │
        │   "version": 2                       │
        │ }                                    │
        └──────────────────────┬───────────────┘
                               ↓
        ┌──────────────────────────────────────┐
        │ Client-side visualization:           │
        │ 1. Show conflict indicator (red bar) │
        │ 2. Highlight line 2 (red background)│
        │ 3. Log to console                   │
        │ 4. Show conflict panel               │
        │ 5. Auto-clear after 5 seconds       │
        └──────────────────────────────────────┘
```

## Presence Tracking Flow

```
┌─────────────────────────────┐
│ User A connects             │
│ @socketio.on('connect')     │
│ - Generate: user_id = "u-a" │
│ - Emit: user_id to client   │
└─────────────┬───────────────┘
              ↓
┌─────────────────────────────────┐
│ User A joins document "doc-123" │
│ emit('join_document', {...})    │
│ - doc_id: "doc-123"             │
│ - user_id: "u-a"                │
└─────────────┬───────────────────┘
              ↓
┌─────────────────────────────────┐
│ @socketio.on('join_document')   │
│ 1. join_room("doc-123")         │
│ 2. PresenceTracker.join(...)    │
│    - users_per_doc["doc-123"] = │
│      {"u-a"}                    │
│ 3. get_presence("doc-123")      │
│    - count: 1, users: ["u-a"]   │
│ 4. emit('presence_updated')     │
│    - broadcast to all in room   │
└─────────────┬───────────────────┘
              ↓ (User A gets this)
┌─────────────────────────────────┐
│ Client updates UI:              │
│ - Presence badge: "👥 1 online" │
│ - Sidebar: shows "user-a" with  │
│   green dot                     │
└─────────────────────────────────┘


┌─────────────────────────────┐
│ User B connects             │
│ - Generate: user_id = "u-b" │
└─────────────┬───────────────┘
              ↓
┌──────────────────────────────────┐
│ User B joins same document        │
│ emit('join_document',             │
│       {"doc_id": "doc-123", ...}) │
└─────────────┬────────────────────┘
              ↓
┌──────────────────────────────────┐
│ @socketio.on('join_document')    │
│ 1. join_room("doc-123")          │
│ 2. PresenceTracker.join(...)     │
│    - users_per_doc["doc-123"] =  │
│      {"u-a", "u-b"}              │
│ 3. get_presence("doc-123")       │
│    - count: 2, users: ["u-a",    │
│      "u-b"]                      │
│ 4. emit('presence_updated',      │
│    {"count": 2, ...})            │
│    - broadcast to room           │
└─────────────┬────────────────────┘
              ↓ (Both users get this)
┌──────────────────────────────────┐
│ Both clients update UI:           │
│ - User A sees: "👥 2 online"     │
│ - User B sees: "👥 2 online"     │
│ - Both sidebars show: u-a, u-b   │
│   both with green dots           │
└──────────────────────────────────┘


┌─────────────────────────────┐
│ User A disconnects          │
│ @socketio.on('disconnect')  │
│ 1. PresenceTracker.leave()  │
│    - users_per_doc[...] =   │
│      {"u-b"}                │
│ 2. get_presence("doc-123")  │
│    - count: 1, users: ["u-b"]
│ 3. emit('presence_updated') │
│    - broadcast to room      │
└─────────────┬───────────────┘
              ↓
┌─────────────────────────────┐
│ User B's client updates:    │
│ - Presence: "👥 1 online"   │
│ - Sidebar: only "user-b"    │
│   shown with green dot      │
└─────────────────────────────┘
```

---

**This architecture ensures:**
- ✅ Real-time synchronization via WebSockets
- ✅ Conflict detection and resolution
- ✅ Presence awareness
- ✅ Persistent storage with replay capability
- ✅ Thread-safe concurrent access
- ✅ Efficient edit debouncing
- ✅ No external database required
