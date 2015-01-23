var inbox = new ReconnectingWebSocket("ws://"+ location.host + "/receive");

inbox.onmessage = function(message) {
  var data = JSON.parse(message.data);

  $.each(data, function( key, val ){
    $("#logs").append(key + ' - ' + val);
    $("#logs").append('<br>');
  });

  $("#logs").append('<hr>');
};

inbox.onclose = function(){
    console.log('inbox closed');
    this.inbox = new WebSocket(inbox.url);
};
