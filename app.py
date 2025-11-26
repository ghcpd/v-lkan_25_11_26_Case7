from collab.server import create_app

app, socketio, store = create_app()

if __name__ == '__main__':
    try:
        import eventlet
        eventlet.monkey_patch()
        socketio.run(app, host='0.0.0.0', port=5000)
    except ImportError:
        socketio.run(app, host='0.0.0.0', port=5000)
