import json
import redis

from gevent import monkey

from socketio import socketio_manage
from socketio.namespace import BaseNamespace
from socketio.mixins import RoomsMixin, BroadcastMixin

from flask import Flask, Response, request, render_template

monkey.patch_all()

app = Flask(__name__)
app.debug = True

REDIS_URL = "redis://54.77.161.206:6379:1"
redis = redis.from_url(REDIS_URL)


# views
@app.route('/')
def rooms():
    return render_template('index.html')


class PlaylistNamespace(BaseNamespace, RoomsMixin, BroadcastMixin):
    nicknames = []

    def initialize(self):
        self.logger = app.logger
        self.clients = list()
        self.pubsub = redis.pubsub()
        self.pubsub.subscribe('playlists')

    def log(self, message):
        self.logger.info("[{0}] {1}".format(self.socket.sessid, message))

    def on_join(self):
        for message in self.pubsub.listen():
            self.log('message: {0}'.format(message))
            if message['type'] == 'message':
                mdata = json.loads(message.get('data'))

                if(mdata['status'] == 'created' or mdata['status'] == 'removed'):
                    label = 'playlists:updated'
                    self.broadcast_event(label)
                elif mdata['status'] == 'updated':
                    label = 'playlist:updated'
                    self.broadcast_event(label, mdata['data'])

        return True


@app.route('/socket.io/<path:remaining>')
def socketio(remaining):
    try:
        socketio_manage(request.environ, {'/playlists': PlaylistNamespace}, request)
    except:
        app.logger.error("Exception while handling socketio connection",
                         exc_info=True)
    return Response()


if __name__ == '__main__':
    app.run()
