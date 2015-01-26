$(function() {

    var socket = io.connect('/playlists');

    socket.on('connect', function () {
        socket.emit('join');
    });

    socket.on('playlists:updated', function (data) {
        message('playlists:updated', '');
    });

    socket.on('playlist:updated', function (data) {
        message('playlist:updated', 'playlist_id:' + data['playlist_id']);
    });

    socket.on('playlists:removed', function (data) {
        message('playlists:removed', 'playlist_id:' + data['playlist_id']);
    });

    function message (from, msg) {
        $('#lines').append($('<p>').append($('<b>').text(from), msg));
    }
});