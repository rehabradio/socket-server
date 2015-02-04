# stdlib imports
import json
import os

# thrid-party imports
import redis
import requests

from flask import Flask
from flask import jsonify
from flask import request
from flask import session
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
r = redis.from_url(REDIS_URL)

socketio = SocketIO(app)


class Listener(Thread):
    def __init__(self, r, channels):
        Thread.__init__(self)
        self.namespace = '/updates'
        self.redis = r
        self.pubsub = self.redis.pubsub()
        self.pubsub.subscribe(channels)

    def run(self):
        """Emits messages recieved from the subscribe channels.
        """
        for message in self.pubsub.listen():
            if message['type'] == 'message':
                mdata = json.loads(message.get('data'))

                # Labels are formatted to identify what has been altered on the server.
                # plural labels (records), means that the record list has been changed.
                # singular labels (record), means that an individual record has been changed.
                if (mdata['status'] == 'updated' or mdata['data']['is_track']):
                    label = '{0}:updated'.format(message['channel'][:-1])
                    socketio.emit(label, mdata['data'], namespace=self.namespace)
                elif(mdata['status'] == 'created' or mdata['status'] == 'deleted'):
                    label = '{0}:updated'.format(message['channel'])
                    socketio.emit(label, namespace=self.namespace)


@app.route('/login')
def login():
    """Log a user in, using a valid google oauth token, with valid associated email.

    Returns json object

    Formatted using jsend style
    http://labs.omniti.com/labs/jsend
    """
    if session.get('user'):
        return jsonify({'status': 'success', 'data': session['user']})

    data = {'status': 'error', 'code': 403}

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
        data = {'status': 'success', 'data': person}

    return jsonify(data)


# Channels to subscribe to on the redis server
channels = ['playlists', 'queues', 'queue-heads']
client = Listener(r, channels)


@socketio.on('connect', namespace='/updates')
def connect():
    """Start the thread, if a user is logged in.
    """
    if session.get('user'):
        emit('connected')

        if client.is_alive():
            client.join()
        else:
            client.start()
    else:
        emit('error', {'code': 403, 'message': 'No user session found.'})


if __name__ == '__main__':
    socketio.run(app)
