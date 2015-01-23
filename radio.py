# stdlib imports
import os

# thrid-party imports
import redis
import gevent
from flask import Flask, render_template
from flask_sockets import Sockets


REDIS_URL = os.environ['REDISCLOUD_URL']
REDIS_CHAN = 'default'

app = Flask(__name__)
app.debug = 'DEBUG' in os.environ

sockets = Sockets(app)
redis = redis.from_url(REDIS_URL)


class RadioListener(object):
    """Interface for registering and updating WebSocket clients."""

    def __init__(self):
        self.clients = list()
        self.pubsub = redis.pubsub()
        self.pubsub.subscribe(REDIS_CHAN)

    def __iter_data(self):
        for message in self.pubsub.listen():
            data = message.get('data')
            if message['type'] == 'message':
                app.logger.info(u'Sending message: {}'.format(data))
                yield data

    def register(self, client):
        """Register a WebSocket connection for Redis updates."""
        self.clients.append(client)

    def send(self, client, data):
        """Send given data to the registered client.
        Automatically discards invalid connections."""
        try:
            client.send(data)
        except Exception:
            self.clients.remove(client)

    def run(self):
        """Listens for new messages in Redis, and sends them to clients."""
        for data in self.__iter_data():
            for client in self.clients:
                gevent.spawn(self.send, client, data)

    def start(self):
        """Maintains Redis subscription in the background."""
        gevent.spawn(self.run)

radio = RadioListener()
radio.start()


@app.route('/')
def hello():
    return render_template('index.html')


@sockets.route('/receive')
def receive(ws):
    """Sends cache writes, via `RadioListener`."""
    radio.register(ws)

    while ws.socket is not None:
        gevent.sleep()
