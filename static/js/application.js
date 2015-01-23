var inbox = new ReconnectingWebSocket("ws://"+ location.host + "/receive");

inbox.onmessage = function(message) {
  console.log(message);
  var data = JSON.parse(message.data);
  console.log(data);
  $("#logs").append(data);
  $("#logs").append('<hr>');
};

inbox.onclose = function(){
    console.log('inbox closed');
    this.inbox = new WebSocket(inbox.url);
};
