# QUICK START GUIDE

## 30-Second Setup

### Step 1: Navigate to Project
```bash
cd v-lkan_25_11_26_Case7
```

### Step 2: Run Setup
**On macOS/Linux**:
```bash
bash setup.sh
```

**On Windows**:
```bash
setup.bat
```

### Step 3: Start Server
```bash
python app.py
```

You should see:
```
2024-11-26 10:30:45,123 - app - INFO - Starting Lightweight Collaboration Platform...
 * Running on http://0.0.0.0:5000
```

### Step 4: Open Browser
Visit: **http://localhost:5000**

---

## First Time Users

### Create a Document
1. Click "Create New" button in header
2. You'll get a new document ID
3. Share the ID with others

### Collaborate
1. Open the same document ID in another browser tab/window
2. See yourself as "user-abc" and "user-def"
3. Start typing - changes sync in real-time!

### View Conflicts
1. Have two people edit the **same line** at the **same time**
2. Red highlighting appears showing conflict
3. Last edit wins (Last-Write-Wins strategy)

---

## Quick Test (Without Server Running)

```bash
# Unit tests (no server needed)
python test_suite.py
```

Expected output:
```
test_document_creation ... ok
test_document_update ... ok
...
Ran 45 tests in 2.341s
OK
```

---

## Multi-User Demo

### Terminal 1: Start Server
```bash
python app.py
```

### Terminal 2: Run Integration Tests
```bash
python integration_tests.py
```

This tests:
- ✅ Real-time editing
- ✅ Presence tracking
- ✅ Conflict detection
- ✅ Persistence
- ✅ Edit logging

---

## File Structure Overview

```
v-lkan_25_11_26_Case7/
├── app.py                    ← Server (start here)
├── requirements.txt          ← Dependencies
├── setup.sh / setup.bat      ← Setup script
├── templates/index.html      ← Web UI
├── static/
│   ├── client.js             ← Frontend logic
│   └── style.css             ← Styling
├── test_suite.py             ← 45 unit tests
├── integration_tests.py       ← Multi-user tests
├── README.md                 ← Full documentation
└── IMPLEMENTATION_GUIDE.md   ← Technical details
```

---

## Common Commands

### Start Server
```bash
python app.py
```

### Run All Tests
```bash
python test_suite.py
```

### Run Integration Tests (needs server)
```bash
python app.py &
python integration_tests.py
```

### View Documents Created
```bash
ls -la data/documents/
```

### View Edit Logs
```bash
cat data/logs/doc_id.jsonl
```

### Install Missing Packages
```bash
pip install -r requirements.txt
```

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+A` | Select all text |
| `Ctrl+C` | Copy |
| `Ctrl+V` | Paste |
| `Ctrl+Z` | Undo (browser) |
| Click "–" (bottom-right) | Toggle debug console |

---

## Tips & Tricks

### Test Real-Time Sync
1. Open http://localhost:5000 in two browser tabs
2. Create document "test-demo"
3. Type in Tab 1, watch it appear in Tab 2 instantly

### View Presence Tracking
- Right sidebar shows "Active Users"
- Updates automatically when people join/leave
- Green dot indicates online status

### Debug Conflicts
- Bottom-right corner: "Debug Console"
- All events logged there
- Check when conflicts detected

### Check What's Stored
```bash
# See all documents
cat data/documents/*.json

# See all edits
cat data/logs/*.jsonl
```

---

## Troubleshooting Quick Fixes

| Problem | Solution |
|---------|----------|
| Port 5000 in use | `lsof -i :5000` then kill process |
| Module not found | Run `pip install -r requirements.txt` |
| No data/ folder | Create with `mkdir -p data/documents data/logs` |
| Server won't start | Check Python version: `python --version` |
| WebSocket fails | Check browser console (F12) for errors |

---

## What's Happening Behind the Scenes

```
User Types
   ↓
400ms Debounce (batches edits)
   ↓
Send to Server (WebSocket)
   ↓
Server detects conflicts (timestamp + lines)
   ↓
Last-Write-Wins applied
   ↓
Broadcast to all clients
   ↓
UI updates in real-time
   ↓
Save to disk (JSON + JSONL)
```

---

## Next Steps

1. **Run Tests**: `python test_suite.py` ✅
2. **Start Server**: `python app.py` ✅
3. **Open Browser**: http://localhost:5000 ✅
4. **Create Document**: Click "Create New" ✅
5. **Test Multi-User**: Open in another tab ✅
6. **Read Full Docs**: See README.md for details ✅

---

## Learn More

- **README.md** - Full feature overview and API documentation
- **IMPLEMENTATION_GUIDE.md** - Technical architecture and design decisions
- **app.py** - Backend source code (well-commented)
- **static/client.js** - Frontend source code (well-commented)
- **test_suite.py** - Examples of how everything works

---

**You're all set! Start with `python app.py` and visit http://localhost:5000** 🚀
