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
from flask import render_template
from flask.ext.cors import CORS
from flask.ext.socketio import SocketIO, emit
from threading import Thread

from gevent import monkey

# local imports
from decorator import crossdomain


monkey.patch_all()


app = Flask(__name__)
app.debug = os.environ.get('DEBUG', False)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'secret!')

CORS(app, resources=r'/*', allow_headers='Content-Type')

REDIS_URL = os.environ.get('REDISCLOUD_URL')
redis = redis.from_url(REDIS_URL)

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

            if (mdata['status'] == 'updated' or mdata['data']['is_track'] == True):
                label = 'playlist:updated'
                socketio.emit(label, mdata['data'], namespace=namespace)
            elif(mdata['status'] == 'created' or mdata['status'] == 'deleted'):
                label = 'playlists:updated'
                socketio.emit(label, namespace=namespace)


def queue_thread():
    """Listens to the redis server, for any updates on the "queues" channel.
    """
    namespace = '/updates'
    pubsub = redis.pubsub()
    pubsub.subscribe('queues')

    for message in pubsub.listen():
        app.logger.info('message: {0}'.format(message))
        if message['type'] == 'message':
            mdata = json.loads(message.get('data'))

            if (mdata['status'] == 'updated' or mdata['data']['is_track']):
                label = 'queue:updated'
                socketio.emit(label, mdata['data'], namespace=namespace)
            elif(mdata['status'] == 'created' or mdata['status'] == 'deleted'):
                label = 'queues:updated'
                socketio.emit(label, namespace=namespace)


@app.route('/')
def index():
    """Endpoint for the playlist and queue updates.
    """
    return render_template('index.html')


@app.route('/login')
@crossdomain(origin='*')
def login():
    """Log a user in, using a valid google oauth token, with valid associated email.
    """
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
        data = {'code': 200}

    return jsonify(data)


@socketio.on('connect', namespace='/updates')
@crossdomain(origin='*')
def connect():
    """Starts reporting the threads.
    """
    if session.get('user'):
        emit(
            'my response',
            {'data': '{0} has joined'.format(session['user']['name'])}
        )
        pthread = Thread(target=playlist_thread)
        pthread.start()
        qthread = Thread(target=queue_thread)
        qthread.start()
    else:
        emit('error', {'code': '403'})


if __name__ == '__main__':
    socketio.run(app)
