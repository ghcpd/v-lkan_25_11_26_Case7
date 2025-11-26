/**
 * Lightweight Collaboration Platform - Client-Side Logic
 * Features:
 * - Real-time editing with WebSocket sync
 * - 400ms debounce for edit events
 * - Conflict visualization with line highlighting
 * - User presence tracking
 * - Edit history display
 */

class CollaborationClient {
    constructor() {
        // WebSocket connection
        this.socket = io();
        this.userId = null;
        this.docId = null;
        this.currentVersion = 0;
        
        // Edit tracking
        this.editCount = 0;
        this.lastEditTime = 0;
        this.pendingEdit = null;
        this.debounceTimer = null;
        this.DEBOUNCE_DELAY = 400; // ms
        
        // Conflict tracking
        this.conflictLines = new Set();
        this.conflictTimeout = null;
        
        // UI Elements
        this.elements = {
            editor: document.getElementById('editor'),
            userId: document.getElementById('userId'),
            docId: document.getElementById('docId'),
            presence: document.getElementById('presence'),
            version: document.getElementById('version'),
            status: document.getElementById('status'),
            stats: document.getElementById('stats'),
            presenceList: document.getElementById('presenceList'),
            historyList: document.getElementById('historyList'),
            conflictIndicator: document.getElementById('conflictIndicator'),
            conflictPanel: document.getElementById('conflictPanel'),
            conflictLines: document.getElementById('conflictLines'),
            loadBtn: document.getElementById('loadBtn'),
            createBtn: document.getElementById('createBtn'),
            clearConflict: document.getElementById('clearConflict'),
            toggleConsole: document.getElementById('toggleConsole'),
            consoleLogs: document.getElementById('consoleLogs'),
            debugConsole: document.getElementById('debugConsole')
        };
        
        // Presence tracking
        this.activeUsers = new Set();
        
        // History tracking
        this.editHistory = [];
        
        this.initializeSocket();
        this.attachEventListeners();
        this.setupDebugConsole();
    }
    
    // ========================================================================
    // Socket.IO Event Handlers
    // ========================================================================
    
    initializeSocket() {
        // User ID assignment
        this.socket.on('user_id', (data) => {
            this.userId = data.user_id;
            this.elements.userId.textContent = `👤 ${this.userId}`;
            this.log(`Assigned user ID: ${this.userId}`, 'info');
        });
        
        // Document loaded
        this.socket.on('document_loaded', (data) => {
            this.docId = data.doc_id;
            this.currentVersion = data.version;
            this.elements.docId.value = this.docId;
            this.elements.version.textContent = `v${this.currentVersion}`;
            this.elements.editor.value = data.content;
            this.updateStatus(`Loaded document: ${this.docId}`);
            this.log(`Document loaded: ${this.docId}`, 'info');
            
            // Request history
            this.socket.emit('request_history', { doc_id: this.docId });
        });
        
        // Document updated
        this.socket.on('document_updated', (data) => {
            if (data.doc_id !== this.docId) return;
            
            // Update if this isn't our own edit
            if (data.user_id !== this.userId) {
                this.elements.editor.value = data.content;
                this.updateStatus(`Updated by ${data.user_id}`);
                this.log(`Document updated by ${data.user_id} (v${data.version})`, 'info');
            }
            
            this.currentVersion = data.version;
            this.elements.version.textContent = `v${this.currentVersion}`;
        });
        
        // Presence updated
        this.socket.on('presence_updated', (data) => {
            this.activeUsers.clear();
            data.users.forEach(user => this.activeUsers.add(user));
            this.updatePresenceUI();
        });
        
        // Conflict detected
        this.socket.on('conflict_detected', (data) => {
            if (data.doc_id !== this.docId) return;
            
            this.conflictLines = new Set(data.affected_lines);
            this.showConflictVisualization(data);
            this.log(`Conflict detected by ${data.user_id} at lines: ${data.affected_lines.join(', ')}`, 'warn');
        });
        
        // History loaded
        this.socket.on('history_loaded', (data) => {
            this.editHistory = data.history;
            this.updateHistoryUI();
            this.log(`History loaded: ${data.edit_count} edits`, 'info');
        });
        
        // Connection events
        this.socket.on('connect', () => {
            this.updateStatus('Connected');
            this.log('WebSocket connected', 'info');
        });
        
        this.socket.on('disconnect', () => {
            this.updateStatus('Disconnected');
            this.log('WebSocket disconnected', 'error');
        });
        
        this.socket.on('connect_error', (error) => {
            this.updateStatus('Connection error');
            this.log(`Connection error: ${error}`, 'error');
        });
    }
    
    // ========================================================================
    // Event Listeners
    // ========================================================================
    
    attachEventListeners() {
        // Editor input with debouncing
        this.elements.editor.addEventListener('input', (e) => {
            this.handleEditorInput(e);
        });
        
        // Load document
        this.elements.loadBtn.addEventListener('click', () => {
            const docId = this.elements.docId.value.trim();
            if (docId) {
                this.loadDocument(docId);
            }
        });
        
        // Create new document
        this.elements.createBtn.addEventListener('click', () => {
            this.createNewDocument();
        });
        
        // Clear conflict visualization
        this.elements.clearConflict.addEventListener('click', () => {
            this.clearConflictVisualization();
        });
        
        // Toggle debug console
        this.elements.toggleConsole.addEventListener('click', () => {
            this.toggleDebugConsole();
        });
        
        // Allow Enter key in document ID field
        this.elements.docId.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.elements.loadBtn.click();
            }
        });
    }
    
    // ========================================================================
    // Editor Input & Debouncing
    // ========================================================================
    
    handleEditorInput(e) {
        const content = this.elements.editor.value;
        
        // Clear previous debounce timer
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }
        
        // Store pending edit
        this.pendingEdit = {
            content: content,
            timestamp: Date.now() / 1000
        };
        
        // Set new debounce timer
        this.debounceTimer = setTimeout(() => {
            this.sendEdit(content);
        }, this.DEBOUNCE_DELAY);
    }
    
    sendEdit(content) {
        if (!this.docId || !this.userId) {
            this.log('Cannot send edit: missing docId or userId', 'error');
            return;
        }
        
        const editData = {
            doc_id: this.docId,
            user_id: this.userId,
            content: content,
            timestamp: Date.now() / 1000,
            edit_id: `${this.userId}-${Date.now()}`
        };
        
        this.socket.emit('edit', editData);
        this.editCount++;
        this.lastEditTime = Date.now();
        
        this.updateStats();
        this.updateStatus('Sending...');
    }
    
    // ========================================================================
    // Document Management
    // ========================================================================
    
    loadDocument(docId) {
        this.elements.docId.value = docId;
        this.socket.emit('join_document', {
            doc_id: docId,
            user_id: this.userId
        });
        this.updateStatus(`Loading document: ${docId}`);
        this.log(`Requested to load document: ${docId}`, 'info');
    }
    
    createNewDocument() {
        fetch('/api/documents', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                this.log(`Created new document: ${data.id}`, 'info');
                this.loadDocument(data.id);
            })
            .catch(err => {
                this.log(`Error creating document: ${err}`, 'error');
            });
    }
    
    // ========================================================================
    // Conflict Visualization
    // ========================================================================
    
    showConflictVisualization(data) {
        // Show conflict indicator
        this.elements.conflictIndicator.classList.remove('hidden');
        this.elements.conflictPanel.classList.remove('hidden');
        
        // Display affected lines
        this.elements.conflictLines.innerHTML = '';
        data.affected_lines.forEach(lineNum => {
            const div = document.createElement('div');
            div.className = 'conflict-line';
            div.textContent = `Line ${lineNum + 1} - conflicted by ${data.user_id}`;
            this.elements.conflictLines.appendChild(div);
        });
        
        // Highlight conflicted lines in editor
        this.highlightConflictLines(data.affected_lines);
        
        // Auto-clear after 5 seconds
        if (this.conflictTimeout) {
            clearTimeout(this.conflictTimeout);
        }
        this.conflictTimeout = setTimeout(() => {
            this.clearConflictVisualization();
        }, 5000);
    }
    
    highlightConflictLines(lineIndices) {
        // Note: Simple visual highlighting via inline styling in console
        // For production, integrate with CodeMirror or similar for precise highlighting
        const lines = this.elements.editor.value.split('\n');
        lineIndices.forEach(idx => {
            if (idx < lines.length) {
                console.warn(`Conflict on line ${idx + 1}: "${lines[idx].substring(0, 50)}..."`);
            }
        });
    }
    
    clearConflictVisualization() {
        this.elements.conflictIndicator.classList.add('hidden');
        this.elements.conflictPanel.classList.add('hidden');
        this.conflictLines.clear();
    }
    
    // ========================================================================
    // Presence UI Updates
    // ========================================================================
    
    updatePresenceUI() {
        this.elements.presence.textContent = `👥 ${this.activeUsers.size} online`;
        
        // Update presence list
        this.elements.presenceList.innerHTML = '';
        if (this.activeUsers.size === 0) {
            this.elements.presenceList.innerHTML = '<p class="empty-state">No users online</p>';
        } else {
            this.activeUsers.forEach(user => {
                const item = document.createElement('div');
                item.className = 'presence-item';
                item.innerHTML = `<span class="user-dot"></span><span>${user}</span>`;
                this.elements.presenceList.appendChild(item);
            });
        }
    }
    
    // ========================================================================
    // History UI Updates
    // ========================================================================
    
    updateHistoryUI() {
        this.elements.historyList.innerHTML = '';
        
        if (this.editHistory.length === 0) {
            this.elements.historyList.innerHTML = '<p class="empty-state">No edits yet</p>';
            return;
        }
        
        // Show last 5 edits
        this.editHistory.slice(-5).forEach((entry, idx) => {
            const item = document.createElement('div');
            item.className = 'history-item';
            const time = new Date(entry.timestamp * 1000).toLocaleTimeString();
            item.innerHTML = `
                <strong>${entry.user_id}</strong> @ ${time}
                <br><small>v${entry.version} (${entry.content_length} chars)</small>
            `;
            this.elements.historyList.appendChild(item);
        });
    }
    
    // ========================================================================
    // Status & Stats
    // ========================================================================
    
    updateStatus(message) {
        this.elements.status.textContent = message;
    }
    
    updateStats() {
        this.elements.stats.textContent = `Edits: ${this.editCount} | Auto-save: On`;
    }
    
    // ========================================================================
    // Debug Console
    // ========================================================================
    
    setupDebugConsole() {
        // Intercept console.log, warn, error
        const originalLog = console.log;
        const originalWarn = console.warn;
        const originalError = console.error;
        
        console.log = (...args) => {
            this.log(args.join(' '), 'info');
            originalLog.apply(console, args);
        };
        
        console.warn = (...args) => {
            this.log(args.join(' '), 'warn');
            originalWarn.apply(console, args);
        };
        
        console.error = (...args) => {
            this.log(args.join(' '), 'error');
            originalError.apply(console, args);
        };
    }
    
    log(message, level = 'info') {
        const logEntry = document.createElement('div');
        logEntry.className = `console-log ${level}`;
        logEntry.textContent = `[${level.toUpperCase()}] ${message}`;
        
        this.elements.consoleLogs.appendChild(logEntry);
        this.elements.consoleLogs.scrollTop = this.elements.consoleLogs.scrollHeight;
        
        // Keep only last 100 logs
        while (this.elements.consoleLogs.children.length > 100) {
            this.elements.consoleLogs.removeChild(this.elements.consoleLogs.firstChild);
        }
    }
    
    toggleDebugConsole() {
        const isHidden = this.elements.debugConsole.style.display === 'none';
        this.elements.debugConsole.style.display = isHidden ? 'flex' : 'none';
    }
}

// Initialize client when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.collaborationClient = new CollaborationClient();
    console.log('Collaboration client initialized');
});
