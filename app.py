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
from flask.ext import login
from flask.ext.login import current_user
from flask.ext.login import login_user
from flask.ext.cors import CORS
from flask.ext.socketio import SocketIO, emit
from threading import Thread

from gevent import monkey


monkey.patch_all()


app = Flask(__name__)
app.debug = os.environ.get('DEBUG', False)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'secret!')


login_manager = login.LoginManager()
login_manager.init_app(app)


CORS(app, allow_headers=['Content-Type', 'Authorization', 'Content-Length', 'X-Requested-With', 'X_GOOGLE_AUTH_TOKEN'])

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


class UserObj(object):
    def __init__(self, user_obj):
        self.id = user_obj['id']
        self.username = user_obj['name']

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)


@login_manager.user_loader
def load_user(id):
    return UserObj(session['user'])


@app.route('/login')
def login():
    """Log a user in, using a valid google oauth token, with valid associated email.
    """
    app.logger.info('current_user: {0}'.format(current_user))

    # if session.get('user'):
    #     app.logger.info('session: user already logged in')
    #     return jsonify({'code': 200, 'message': session['user']})

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
        session['user_id'] = person['id']
        data = {'code': 200, 'message': session['user']}
        login_user(UserObj(session['user']))

    return jsonify(data)


@socketio.on('connect', namespace='/updates')
def connect():
    """Starts reporting the threads.
    """
    Thread(target=playlist_thread).start()
    Thread(target=queue_thread).start()

    app.logger.info('session: {0}'.format(session))
    if session.get('user'):
        app.logger.info('LOGGED IN')
        emit(
            'my response',
            {'data': '{0} has joined'.format(session['user']['name'])}
        )
        # Thread(target=playlist_thread).start()
        # Thread(target=queue_thread).start()
    else:
        app.logger.info('NOT LOGGED IN')
        # emit('error', {'code': '403'})


if __name__ == '__main__':
    socketio.run(app)
