(function(){
    const socket = io();
    let userId = localStorage.getItem('user_id');
    if(!userId){
        userId = 'user-' + Math.random().toString(36).slice(2, 8);
        localStorage.setItem('user_id', userId);
    }

    const docIdEl = document.getElementById('docId');
    const joinBtn = document.getElementById('joinBtn');
    const editor = document.getElementById('editor');
    const preview = document.getElementById('preview');
    const presenceEl = document.getElementById('presence');
    const historyBtn = document.getElementById('historyBtn');

    let currentDoc = null;
    let lastContent = '';
    let version = 0;

    let debounceTimer = null;
    function debounceSend() {
        if(debounceTimer) clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            sendEdit();
        }, 400);
    }

    function sendEdit(){
        if(!currentDoc) return;
        const content = editor.value;
        const edited_lines = computeEditedLines(lastContent, content);
        socket.emit('edit', {doc_id: currentDoc, content, user_id: userId, edited_lines});
        lastContent = content;
    }

    function computeEditedLines(oldContent, newContent){
        if(oldContent === newContent) return [-1, -1];
        const oldLines = oldContent.split('\n');
        const newLines = newContent.split('\n');
        let start = 0;
        while(start < oldLines.length && start < newLines.length && oldLines[start] === newLines[start]) start++;
        let endOld = oldLines.length -1;
        let endNew = newLines.length -1;
        while(endOld >= start && endNew >= start && oldLines[endOld] === newLines[endNew]){ endOld--; endNew--; }
        return [start, endNew >= start ? endNew : start];
    }

    function updatePreview(content, highlightRanges=[]){
        const lines = content.split('\n');
        const html = lines.map((ln, idx) => {
            const cls = highlightRanges.some(r => idx >= r[0] && idx <= r[1]) ? 'line conflict' : 'line';
            return `<span class="${cls}" data-line="${idx}">${escapeHtml(ln)}</span>`;
        }).join('\n');
        preview.innerHTML = html;
    }

    function escapeHtml(s){
        return s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c]));
    }

    joinBtn.addEventListener('click', () => {
        if(!docIdEl.value) return alert('Please enter a doc ID');
        if(currentDoc) socket.emit('leave', {doc_id: currentDoc});
        currentDoc = docIdEl.value;
        socket.emit('join', {doc_id: currentDoc, user_id: userId});
    });

    editor.addEventListener('input', () => {
        debounceSend();
        // live preview without highlight
        updatePreview(editor.value);
    });

    historyBtn.addEventListener('click', () => {
        if(!currentDoc) return alert('Join a doc first');
        socket.emit('get_history', {doc_id: currentDoc});
    });

    socket.on('doc_state', data => {
        if(data.doc_id !== currentDoc) return;
        editor.value = data.content || '';
        lastContent = editor.value;
        updatePreview(editor.value);
        version = data.version || 0;
    });

    socket.on('doc_update', data => {
        if(data.doc_id !== currentDoc) return;
        editor.value = data.content || '';
        lastContent = editor.value;
        updatePreview(editor.value);
        version = data.version || version;
    });

    socket.on('presence', data => {
        presenceEl.innerText = 'Users online: ' + (data.count || 0);
    });

    socket.on('history', data => {
        console.log('History', data);
        const entries = data.edits || [];
        alert('History entries: ' + entries.length + '\nCheck console for details');
        console.table(entries.map(e => ({timestamp: new Date(e.timestamp*1000).toLocaleString(), user_id: e.user_id, version: e.version}))); 
    });

    socket.on('conflict', data => {
        console.warn('Conflict detected', data);
        if(data.doc_id !== currentDoc) return;
        const ranges = [];
        try{
            // add new_edit range
            const n = data.new_edit.edited_lines; if(n) ranges.push(n);
            data.conflicts.forEach(c => { if(c.edited_lines) ranges.push(c.edited_lines); });
        } catch(e) {}
        updatePreview(editor.value, ranges);
    });
})();
