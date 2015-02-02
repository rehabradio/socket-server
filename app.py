# stdlib imports
import json
import os

# thrid-party imports
import redis
import requests

from flask import Flask
from flask import request
from flask.ext.cors import CORS
from flask.ext.socketio import SocketIO, emit
from threading import Thread

from gevent import monkey


monkey.patch_all()


app = Flask(__name__)
app.debug = os.environ.get('DEBUG', False)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'secret!')

CORS(app, allow_headers=['Content-Type', 'Authorization', 'Content-Length', 'X-Requested-With', 'X_GOOGLE_AUTH_TOKEN'])

REDIS_URL = os.environ.get('REDISCLOUD_URL')
redis = redis.from_url(REDIS_URL)

socketio = SocketIO(app)


def playlist_thread():
    """Listens to the redis server, for any updates on the "playlists" channel.
    """
    thread_handler('playlist')


def queue_thread():
    """Listens to the redis server, for any updates on the "queues" channel.
    """
    thread_handler('queue')


def queue_head_thread():
    """Listens to the redis server, for any updates on the "queue-heads" channel.
    """
    thread_handler('queue-head')


def thread_handler(channel):
    namespace = '/updates'
    pubsub = redis.pubsub()
    pubsub.subscribe('{0}s'.format(channel))

    for message in pubsub.listen():
        app.logger.info('message: {0}'.format(message))
        if message['type'] == 'message':
            mdata = json.loads(message.get('data'))

            if (mdata['status'] == 'updated' or mdata['data']['is_track']):
                label = '{0}:updated'.format(channel)
                socketio.emit(label, mdata['data'], namespace=namespace)
            elif(mdata['status'] == 'created' or mdata['status'] == 'deleted'):
                label = '{0}s:updated'.format(channel)
                socketio.emit(label, namespace=namespace)


@socketio.on('connect', namespace='/updates')
def connect():
    """Starts reporting the threads.
    """
    emit('connected', {'data': 'Connected'})
    Thread(target=playlist_thread).start()
    Thread(target=queue_thread).start()
    Thread(target=queue_head_thread).start()


if __name__ == '__main__':
    socketio.run(app)
