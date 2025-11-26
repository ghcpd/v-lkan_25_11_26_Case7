# v-lkan_25_11_26_Case7

This workspace contains a lightweight collaborative editor demo under `collab/`.

Features:
- Real-time editing using Flask-SocketIO
- Presence awareness and anonymous IDs
- Debounced client-side edits
- Append-only JSONL persistence
- Conflict detection & visualization simulation

Try it out:
1. cd collab
2. Run on Windows: `run_server.bat` or on Unix/macOS: `./run_server.sh`
		- To use a specific Python executable (for example `D:\package\venv310\Scripts\python.exe`) to create the virtualenv and run server/tests, use the wrapper scripts.
			Prefer the 'clean' versions (they're less likely to be corrupted):
			- Start server using your Python: `run_server_with_python_clean.bat "D:\package\venv310\Scripts\python.exe"`
			- Run tests using your Python: `run_test_with_python_clean.bat "D:\package\venv310\Scripts\python.exe"`
3. Open `http://localhost:5000` in multiple browsers or tabs

Run tests:
1. cd collab
2. Setup (Unix): `./setup.sh` or Windows: `setup.bat`
3. Run tests: `./run_test.sh` or `run_test.bat`

See `collab/TEST_REPORT_TEMPLATE.md` for a simple test reporting template.