import os
import json
import redis

from gevent import monkey
monkey.patch_all()

import time
from threading import Thread
from flask import Flask, render_template, session, request
from flask.ext.socketio import SocketIO, emit

app = Flask(__name__)
app.debug = os.environ.get('DEBUG', False)

REDIS_URL = os.environ.get('REDISCLOUD_URL')
redis = redis.from_url(REDIS_URL)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'secret!')
socketio = SocketIO(app)


def playlist_thread():
    """Listens to the redis server, for any updates on the "playlists" channel.
    """
    namespace = '/updates'
    pubsub = redis.pubsub()
    pubsub.subscribe('playlists')

    for message in pubsub.listen():
        app.logger.info('message: {0}'.format(message))
        if message['type'] == 'message':
            mdata = json.loads(message.get('data'))

            if (mdata['status'] == 'updated' or mdata['data'].get('track_id')):
                label = 'playlist:updated'
                socketio.emit(label, mdata['data'], namespace=namespace)
            elif(mdata['status'] == 'created' or mdata['status'] == 'removed'):
                label = 'playlists:updated'
                socketio.emit(label, namespace=namespace)



def queue_thread():
    """Listens to the redis server, for any updates on the "playlists" channel.
    """
    namespace = '/updates'
    pubsub = redis.pubsub()
    pubsub.subscribe('queues')

    for message in pubsub.listen():
        app.logger.info('message: {0}'.format(message))
        if message['type'] == 'message':
            mdata = json.loads(message.get('data'))

            if (mdata['status'] == 'updated' or mdata['data'].get('track_id')):
                label = 'queue:updated'
                socketio.emit(label, mdata['data'], namespace=namespace)
            elif(mdata['status'] == 'created' or mdata['status'] == 'removed'):
                label = 'queues:updated'
                socketio.emit(label, namespace=namespace)


@app.route('/')
def index():
    """Endpoint for the playlist and queue updates.
    """
    pthread = Thread(target=playlist_thread)
    pthread.start()
    qthread = Thread(target=queue_thread)
    qthread.start()
    return render_template('index.html')


@socketio.on('connect', namespace='/updates')
def connect():
    emit('my response', {'data': 'Connected', 'count': 0})


if __name__ == '__main__':
    socketio.run(app)
