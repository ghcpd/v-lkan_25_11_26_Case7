(() => {
  // Allow the Socket.IO client to choose the best transport (websocket or polling).
  const socket = io();
  let sessionId = null, userId = null;
  let currentDoc = null;
  let lastLines = [];
  const editor = document.getElementById('editor');
  const docIdInput = document.getElementById('docId');
  const joinBtn = document.getElementById('join');
  const newDocBtn = document.getElementById('newDoc');
  const presenceEl = document.getElementById('presence');
  const sessionEl = document.getElementById('sessionId');
  const userEl = document.getElementById('userId');
  const logEl = document.getElementById('log');

  function log(...args) {
    console.log(...args);
    const li = document.createElement('div');
    li.textContent = `[${new Date().toISOString()}] ${args.join(' ')} `;
    logEl.prepend(li);
  }

  socket.on('session', (payload) => {
    sessionId = payload.session_id;
    userId = payload.user_id;
    sessionEl.textContent = sessionId;
    userEl.textContent = userId;
    log('session', JSON.stringify(payload));
  });

  socket.on('document', (payload) => {
    if (!payload || payload.doc_id !== currentDoc) return;
    // Accept authoritative content
    renderContent(payload.content || '');
    presenceEl.textContent = payload.presence ?? presenceEl.textContent;
    log('document update', payload.doc_id, `(len=${(payload.content||'').length})`);
  });

  socket.on('presence', (payload) => {
    if (payload.doc_id !== currentDoc) return;
    presenceEl.textContent = payload.presence;
    log('presence', payload.presence);
  });

  socket.on('conflict', (payload) => {
    if (payload.doc_id !== currentDoc) return;
    // Highlight conflicting lines
    log('conflict', JSON.stringify(payload));
    const conflicts = payload.conflicts || [];
    // clear previous conflict highlights
    editor.querySelectorAll('.line').forEach(el => el.classList.remove('conflict'));
    for (const li of conflicts) {
      const el = editor.querySelector(`.line[data-line-index='${li}']`);
      if (el) el.classList.add('conflict');
    }
  });

  function renderContent(text) {
    // Render each line into a separate div so we can highlight them
    const lines = text.split('\n');
    lastLines = lines.slice();
    editor.innerHTML = '';
    lines.forEach((ln, idx) => {
      const d = document.createElement('div');
      d.className = 'line';
      d.setAttribute('data-line-index', idx);
      // preserve trailing space
      d.textContent = ln || '\u200B';
      editor.appendChild(d);
    });
    // Keep an empty trailing line available for typing
    if (lines.length === 0 || text.endsWith('\n')) {
      const idx = lines.length;
      const d = document.createElement('div');
      d.className = 'line';
      d.setAttribute('data-line-index', idx);
      d.innerHTML = '\u200B';
      editor.appendChild(d);
    }
  }

  function getContentFromEditor() {
    // Reconstruct content from per-line divs
    const nodes = Array.from(editor.querySelectorAll('.line'));
    return nodes.map(n => n.textContent === '\u200B' ? '' : n.textContent).join('\n');
  }

  function diffLines(oldLines, newLines) {
    const changed = [];
    const maxL = Math.max(oldLines.length, newLines.length);
    for (let i = 0; i < maxL; i++) {
      const a = oldLines[i] || '';
      const b = newLines[i] || '';
      if (a !== b) changed.push(i);
    }
    return changed;
  }

  let debounceTimer = null;
  function scheduleUpdate() {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      const newContent = getContentFromEditor();
      const newLines = newContent.split('\n');
      const changed = diffLines(lastLines, newLines);
      lastLines = newLines.slice();
      if (!currentDoc) return;
      const payload = { doc_id: currentDoc, content: newContent, ts: Date.now() / 1000.0, user_id: userId, lines: changed };
      socket.emit('update', payload);
      log('sent update', JSON.stringify({ doc: currentDoc, changed: changed }));
    }, 400);
  }

  // capture typing in editor: use input events and contentEditable mutations
  editor.addEventListener('input', () => {
    // reset conflict styling while typing
    editor.querySelectorAll('.line.conflict').forEach(el => el.classList.remove('conflict'));
    scheduleUpdate();
  });

  joinBtn.addEventListener('click', async () => {
    const doc = docIdInput.value.trim() || 'default';
    currentDoc = doc;
    // fetch current document
    try {
      const r = await fetch(`/doc/${encodeURIComponent(doc)}`);
      const j = await r.json();
      renderContent(j.content || '');
      presenceEl.textContent = j.presence || 0;
      socket.emit('join', { doc_id: doc });
      log('joined', doc);
    } catch (err) {
      log('failed to fetch doc', err.message);
    }
  });

  newDocBtn.addEventListener('click', () => {
    // random short doc id
    const id = 'doc-' + Math.random().toString(36).slice(2, 9);
    docIdInput.value = id;
    currentDoc = id;
    renderContent('');
    socket.emit('join', { doc_id: id });
    log('created and joined', id);
  });

  // when user presses Enter at end of a line, ensure a new line element exists
  editor.addEventListener('keydown', (ev) => {
    if (ev.key === 'Tab') {
      ev.preventDefault();
      document.execCommand('insertText', false, '\t');
    }
  });

})();
