// var inbox = new ReconnectingWebSocket("ws://"+ location.host + "/receive");

// inbox.onmessage = function(message) {
//     console.log(message)
//     $("#logs").append(message.data);

//     $("#logs").append('<hr>');
// };

// inbox.onclose = function(){
//     console.log('inbox closed');
//     this.inbox = new WebSocket(inbox.url);
// };
socket = io(location.host + "/receive");


// var globalEvent = "*";
// socket.$emit = function (name) {
//     if(!this.$events) return false;
//     for(var i=0;i<2;++i){
//         if(i==0 && name==globalEvent) continue;
//         var args = Array.prototype.slice.call(arguments, 1-i);
//         var handler = this.$events[i==0?name:globalEvent];
//         if(!handler) handler = [];
//         if ('function' == typeof handler) handler.apply(this, args);
//         else if (io.util.isArray(handler)) {
//             var listeners = handler.slice();
//             for (var i=0, l=listeners.length; i<l; i++)
//                 listeners[i].apply(this, args);
//         } else return false;
//     }
//     return true;
// };
// socket.on(globalEvent,function(event){
//     var args = Array.prototype.slice.call(arguments, 1);
//     console.log("Global Event = "+event+"; Arguments = "+JSON.stringify(args));
// });

socket.on('playlists:updated', function (data) {
    console.log('############################');
    console.log(data);
});