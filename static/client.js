(function(){
  const socket = io();
  const editor = document.getElementById('editor');
  const presenceSpan = document.getElementById('presence-count');
  const userIdSpan = document.getElementById('user-id-val');
  const conflictBanner = document.getElementById('conflict-banner');
  const DEBOUNCE_MS = 400;

  let userId = null;
  let debounceTimer = null;
  let lastKnownContent = editor ? editor.value : '';
  let lastVersion = typeof INITIAL_VERSION !== 'undefined' ? INITIAL_VERSION : 0;

  socket.on('connect', () => {
    socket.emit('join_document', {doc_id: DOC_ID});
  });

  socket.on('user_assigned', (data) => {
    userId = data.user_id;
    if (userIdSpan) userIdSpan.textContent = userId;
  });

  socket.on('document_state', (data) => {
    if (data.doc_id !== DOC_ID) return;
    lastKnownContent = data.content;
    lastVersion = data.version;
    if (editor && editor.value !== data.content) {
      editor.value = data.content;
    }
  });

  socket.on('document_updated', (data) => {
    if (data.doc_id !== DOC_ID) return;
    lastVersion = data.version;
    // if update is from self and content matches, skip; otherwise update to authoritative state
    if (data.user_id === userId && editor.value === data.content) return;
    if (editor && editor.value !== data.content) {
      editor.value = data.content;
      lastKnownContent = data.content;
    }
  });

  socket.on('presence', (data) => {
    if (data.doc_id !== DOC_ID) return;
    if (presenceSpan) presenceSpan.textContent = data.count;
  });

  socket.on('conflict', (data) => {
    if (data.doc_id !== DOC_ID) return;
    console.warn('Conflict detected', data);
    if (conflictBanner) {
      conflictBanner.classList.remove('hidden');
      const lines = data.lines || [];
      conflictBanner.textContent = `Conflict on lines: ${lines.join(', ')} (with ${data.conflicts.map(c => c.user_id).join(', ')})`;
      // hide after 3 seconds
      setTimeout(() => conflictBanner.classList.add('hidden'), 3000);
    }
    if (editor) {
      editor.classList.add('conflict');
      setTimeout(() => editor.classList.remove('conflict'), 1000);
    }
  });

  function sendEdit() {
    if (!editor) return;
    const content = editor.value;
    if (content === lastKnownContent) return;
    lastKnownContent = content;
    socket.emit('edit_document', {doc_id: DOC_ID, content: content, version: lastVersion});
  }

  if (editor) {
    editor.addEventListener('input', () => {
      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = setTimeout(sendEdit, DEBOUNCE_MS);
    });
  }

  window.addEventListener('beforeunload', () => {
    socket.emit('leave_document', {doc_id: DOC_ID});
  });
})();
