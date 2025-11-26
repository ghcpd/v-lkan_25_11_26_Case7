import time
import socketio

sio1 = socketio.Client()
sio2 = socketio.Client()

sio1_events = []
sio2_events = []

@sio1.on('document_updated')
def on_du1(data):
    sio1_events.append(('document_updated', data))

@sio2.on('document_updated')
def on_du2(data):
    sio2_events.append(('document_updated', data))

@sio1.on('document_state')
def on_state1(data):
    sio1_events.append(('document_state', data))

@sio2.on('document_state')
def on_state2(data):
    sio2_events.append(('document_state', data))


def main():
    sio1.connect('http://localhost:5000')
    sio2.connect('http://localhost:5000')

    doc_id = 'test-doc-cli'
    sio1.emit('join_document', {'doc_id': doc_id})
    sio2.emit('join_document', {'doc_id': doc_id})

    time.sleep(0.5)
    sio1_events.clear(); sio2_events.clear()

    sio1.emit('edit_document', {'doc_id': doc_id, 'content': 'hello from client1'})

    time.sleep(0.5)
    print('sio1 events:', sio1_events)
    print('sio2 events:', sio2_events)

    sio1.disconnect()
    sio2.disconnect()

if __name__ == '__main__':
    main()
