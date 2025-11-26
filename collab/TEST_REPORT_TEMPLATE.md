# Collaboration App Test Report Template

Tested components:
- Real-time editing (WebSocket events)
- Presence counts
- Edit persistence (JSONL logs)
- Conflict detection and visualization
- Multi-document behavior

Test cases
1. Join/Presence
- Steps:
  - Start server
  - Client A joins doc 'doc1'
  - Client B joins doc 'doc1'
- Expected: presence counts show 2; both clients get doc state
- Results: [PASS/FAIL], notes

2. Edit propagation
- Steps:
  - Clients A and B join doc 'doc2'
  - A edits and emits an update
- Expected: B receives doc_update with content (LWW)
- Results: [PASS/FAIL], notes

3. Persistence and replay
- Steps:
  - A edits doc 'doc3'
  - Stop server, start server
  - Join doc 'doc3'
- Expected: Document content restored from JSONL logs
- Results: [PASS/FAIL], notes

4. Conflict detection
- Steps:
  - Two clients edit overlapping lines within the conflict window
- Expected: conflict event is broadcast and client preview highlights ranges
- Results: [PASS/FAIL], notes

5. Multiple documents
- Steps:
  - Create multiple docs and ensure isolation
- Expected: edits to docA do not affect docB
- Results: [PASS/FAIL], notes


Additional notes:
- Logs location: logs/ (JSONL)
- Run 'run_test.sh' to execute tests
