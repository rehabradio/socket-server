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
        for message in self.pubsub.listen():
            # app.logger.info('message: {0}'.format(message))
            if message['type'] == 'message':
                mdata = json.loads(message.get('data'))
                # app.logger.info('mdata: {0}'.format(mdata))

                if (mdata['status'] == 'updated' or mdata['data']['is_track']):
                    label = '{0}:updated'.format(message['channel'][:-1])
                    socketio.emit(label, mdata['data'], namespace=self.namespace)
                elif(mdata['status'] == 'created' or mdata['status'] == 'deleted'):
                    label = '{0}:updated'.format(message['channel'])
                    socketio.emit(label, namespace=self.namespace)


@app.route('/login')
def login():
    """Log a user in, using a valid google oauth token, with valid associated email.
    """
    if session.get('user'):
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


channels = ['playlists', 'queues', 'queue-heads']
client = Listener(r, channels)


@socketio.on('connect', namespace='/updates')
def connect():
    """Starts reporting the threads.
    """
    if session.get('user'):
        emit(
            'connected',
            {'data': '{0} has joined'.format(session['user']['name'])}
        )
        if client.is_alive():
            client.join()
        else:
            client.start()

    else:
        emit('error', {'code': '403'})


if __name__ == '__main__':
    socketio.run(app)
