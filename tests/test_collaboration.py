import time

from collab.store import DocumentStore


def get_events(client, name=None):
    events = client.get_received()
    if name is None:
        return events
    return [e for e in events if e.get('name') == name]


def test_real_time_collaboration_propagates_edits(app_socket_store, client_factory):
    app, socketio, store = app_socket_store
    doc_id = "doc-collab"
    store.get_or_create(doc_id)

    c1 = client_factory()
    c2 = client_factory()

    c1.emit('join_document', {'doc_id': doc_id})
    c2.emit('join_document', {'doc_id': doc_id})

    # drain initial events
    c1.get_received(); c2.get_received()

    c1.emit('edit_document', {'doc_id': doc_id, 'content': 'hello'})

    events = get_events(c2, 'document_updated')
    assert any(ev['args'][0]['content'] == 'hello' for ev in events), events


def test_persistence_replay_rebuilds_content(tmp_data_dir):
    store = DocumentStore(data_dir=str(tmp_data_dir))
    store.load_all()
    doc_id = 'doc-persist'
    store.apply_edit(doc_id, 'user-x', 'persisted content')

    # new store loads from logs
    store2 = DocumentStore(data_dir=str(tmp_data_dir))
    store2.load_all()
    content, version = store2.get_content(doc_id)
    assert content == 'persisted content'
    assert version >= 1


def test_conflict_detection_broadcasts(app_socket_store, client_factory):
    app, socketio, store = app_socket_store
    doc_id = 'doc-conflict'
    store.get_or_create(doc_id)
    c1 = client_factory()
    c2 = client_factory()
    c1.emit('join_document', {'doc_id': doc_id})
    c2.emit('join_document', {'doc_id': doc_id})
    # drain
    c1.get_received(); c2.get_received()

    c1.emit('edit_document', {'doc_id': doc_id, 'content': 'line1'})
    time.sleep(0.1)
    c2.emit('edit_document', {'doc_id': doc_id, 'content': 'line1 edited by user2'})

    conflicts = get_events(c2, 'conflict')
    assert conflicts, "Expected a conflict event"
    # Ensure conflict refers to line 0
    conflict_data = conflicts[0]['args'][0]
    assert 0 in conflict_data.get('lines', [])


def test_multi_document_isolation(app_socket_store, client_factory):
    app, socketio, store = app_socket_store
    doc_a = 'doc-A'
    doc_b = 'doc-B'
    store.get_or_create(doc_a)
    store.get_or_create(doc_b)

    cA = client_factory()
    cB = client_factory()

    cA.emit('join_document', {'doc_id': doc_a})
    cB.emit('join_document', {'doc_id': doc_b})

    # drain initial events
    cA.get_received(); cB.get_received()

    cA.emit('edit_document', {'doc_id': doc_a, 'content': 'A content'})
    time.sleep(0.05)

    # cB should not get updates for doc_a
    updates_b = get_events(cB, 'document_updated')
    assert not updates_b, updates_b

    # cA should get its update back (authoritative broadcast)
    updates_a = get_events(cA, 'document_updated')
    assert any(ev['args'][0]['content'] == 'A content' for ev in updates_a)
