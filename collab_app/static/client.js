(function(){
  const socket = io();
  let userId = null;
  let currentDoc = null;
  const debounceMs = 400;
  let debounceTimer = null;
  let lastContent = '';

  function fetchDocs(){
    fetch('/docs').then(r => r.json()).then(d => {
      const list = document.getElementById('docList');
      list.innerHTML = '';
      d.docs.forEach(doc => {
        const li = document.createElement('li');
        const btn = document.createElement('button');
        btn.innerText = 'Join ' + doc;
        btn.onclick = () => joinDoc(doc);
        li.appendChild(btn);
        li.appendChild(document.createTextNode(' ' + doc));
        list.appendChild(li);
      });
    });
  }

  function joinDoc(docId){
    currentDoc = docId;
    document.getElementById('docTitle').innerText = 'Doc: ' + docId;
    socket.emit('join_doc', {doc_id: docId, user_id: userId});
  }

  function createDoc(){
    let id = 'doc-' + Math.random().toString(36).substr(2, 6);
    socket.emit('create_doc', {doc_id: id, content: 'New doc\n', user_id: userId});
    setTimeout(fetchDocs, 200);
  }

  socket.on('connect', () => {
    console.log('connected');
  });
  socket.on('welcome', (d) => {
    userId = d.user_id;
    document.getElementById('userId').innerText = 'User: ' + userId;
    fetchDocs();
  });

  socket.on('doc_created', (d) => {
    fetchDocs();
  });

  socket.on('doc_state', (d) => {
    if(d.doc_id !== currentDoc) return;
    lastContent = d.content;
    document.getElementById('editor').value = d.content;
  });

  socket.on('doc_update', (d) => {
    if(d.doc_id !== currentDoc) return;
    lastContent = d.content;
    document.getElementById('editor').value = d.content;
  });

  socket.on('presence_update', (d) => {
    if(d.doc_id !== currentDoc) return;
    document.getElementById('presenceCount').innerText = d.count;
  });

  socket.on('conflict', (d) => {
    if(d.doc_id !== currentDoc) return;
    // very simple visualization: flash the editor background
    const conf = document.getElementById('conflictMsg');
    conf.style.display = 'block';
    setTimeout(()=>{ conf.style.display = 'none'; }, 2000);
    console.warn('Conflict detected for doc', d.doc_id, d.conflicts);
  });

  socket.on('history', (d) => {
    console.log('history', d);
  });

  document.getElementById('createDoc').onclick = createDoc;

  const editor = document.getElementById('editor');
  editor.addEventListener('input', (e) => {
    if(!currentDoc) return;
    if(debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      const content = editor.value;
      const startLineEndLine = computeLineRange(lastContent, content);
      socket.emit('edit', {doc_id: currentDoc, content: content, user_id: userId, ts: Date.now()/1000.0, start_line: startLineEndLine[0], end_line: startLineEndLine[1]});
      lastContent = content;
    }, debounceMs);
  });

  function computeLineRange(oldContent, newContent){
    const oldLines = oldContent.split('\n');
    const newLines = newContent.split('\n');
    let start = null;
    let end = null;
    const maxLen = Math.max(oldLines.length, newLines.length);
    for(let i=0; i<maxLen; i++){
      if(oldLines[i] !== newLines[i]){
        if(start === null) start = i+1;
        end = i+1;
      }
    }
    if(start === null) return [1,1];
    return [start, end];
  }

  // Request history demo every 5s
  setInterval(()=>{
    if(currentDoc) socket.emit('request_history', {doc_id: currentDoc});
  }, 5000);

})();
