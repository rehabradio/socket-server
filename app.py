# stdlib imports
import json
import os

# thrid-party imports
import redis
import requests

from flask import Flask
from flask import jsonify
from flask import session
from flask import request
from flask.ext.cors import CORS
from flask.ext.socketio import SocketIO, emit
from threading import Thread

from gevent import monkey


monkey.patch_all()


app = Flask(__name__)
app.debug = os.environ.get('DEBUG', False)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'secret!')


CORS(
    app,
    origins=[
        'http://localhost',
        'http://rehabradio.herokuapp.com',
    ],
    allow_headers=[
        'Content-Type',
        'Authorization',
        'Content-Length',
        'X-Requested-With',
        'X_GOOGLE_AUTH_TOKEN'
    ],
    supports_credentials=True
)

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


@app.route('/login')
def login():
    """Log a user in, using a valid google oauth token, with valid associated email.
    """
    app.logger.info('session: {0}'.format(session))
    if session.get('user'):
        app.logger.info('User session found')
        return jsonify({'code': 200, 'message': session['user']})

    data = {'code': 403}

    # Retrieve the access token from the request header
    access_token = request.headers.get('X-Google-Auth-Token')

    if not access_token:
        data['message'] = 'X-Google-Auth-Token not found'
    else:
        # Validated the token and pull down the user details
        params = {'alt': 'json', 'access_token': access_token}
        r = requests.get(
            'https://www.googleapis.com/oauth2/v1/userinfo',
            params=params
        )
        person = r.json()

        # Ensure a valid json object is returned
        if person.get('error'):
            return jsonify(person.get('error'))

        if person['verified_email'] is False:
            data['message'] = 'email not verified'
            return jsonify(data)

        # Retrieve the whitelisted domains set in the .env file
        white_listed_domains = os.environ.get('GOOGLE_WHITE_LISTED_DOMAINS', '').split(',')

        # Ensure the users domain exists within the whilelist
        if (person.get('hd') and person.get('hd') not in white_listed_domains):
            data['message'] = 'Email domain not whitelisted.'
            return jsonify(data)

        session['user'] = person
        data = {'code': 200, 'message': session['user']}
        app.logger.info('person: {0}'.format(person))

    return jsonify(data)


@socketio.on('connect', namespace='/updates')
def connect():
    """Starts reporting the threads.
    """
    Thread(target=playlist_thread).start()
    Thread(target=queue_thread).start()
    Thread(target=queue_head_thread).start()
    if session.get('user'):
        emit(
            'connected',
            {'data': '{0} has joined'.format(session['user']['name'])}
        )
        # Thread(target=playlist_thread).start()
        # Thread(target=queue_thread).start()
        # Thread(target=queue_head_thread).start()
    else:
        emit('error', {'code': '403'})


if __name__ == '__main__':
    socketio.run(app)
