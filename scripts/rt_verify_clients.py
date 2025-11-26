#!/usr/bin/env python
"""
Headless test script: connect two socketio clients, join same doc, send update from client A,
and verify client B receives document event
"""
import time
import sys
import socketio

BASE = 'http://127.0.0.1:5000'
doc = 'verify-doc'

received = {'b': None}

def main():
    # Force polling transport to avoid WebSocket requirement on dev server
    sio_a = socketio.Client()
    sio_b = socketio.Client()

    @sio_b.on('document')
    def doc_b(payload):
        print('B received document', payload)
        received['b'] = payload

    # connect both
    print('Connecting A...')
    sio_a.connect(BASE, transports=['polling'])
    print('Connecting B...')
    sio_b.connect(BASE, transports=['polling'])

    # Join doc
    time.sleep(0.1)
    print('A join')
    sio_a.emit('join', {'doc_id': doc})
    print('B join')
    sio_b.emit('join', {'doc_id': doc})

    time.sleep(0.2)
    # send update from A
    print('A sends update')
    payload = {'doc_id': doc, 'content': 'hello\nfrom A\n', 'ts': time.time(), 'user_id': 'A', 'lines': [0,1]}
    sio_a.emit('update', payload)

    # wait for B to get update
    t0 = time.time()
    while time.time() - t0 < 5.0 and received['b'] is None:
        time.sleep(0.1)

    if received['b']:
        print('SUCCESS: B received update')
        return 0
    else:
        print('FAIL: B did not receive update')
        return 2

if __name__ == '__main__':
    sys.exit(main())
