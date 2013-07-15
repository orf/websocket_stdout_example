from twisted.internet import reactor, protocol
from autobahn.websocket import WebSocketServerFactory, \
                               WebSocketServerProtocol, \
                               listenWS
from twisted.python.log import startLogging, msg
import sys
startLogging(sys.stdout)

# Examples:
# runner.py /bin/sh -c "tail -f /var/log/nginx/access.log | grep -v secret_admin_page" --line-buffered | awk '{\$1=\"\"; print}'"
# runner.py tail tail -F /var/log/nginx/access.log

COMMAND_NAME = sys.argv[1]
COMMAND_ARGS = sys.argv[1:]
LOCAL_ONLY = False
DEBUG = True


class ProcessProtocol(protocol.ProcessProtocol):
    def __init__(self, websocket_factory):
        self.ws = websocket_factory
        self.buffer = []
        
    def outReceived(self, message):
        self.ws.broadcast(message)
        self.buffer.append(message)
        self.buffer = self.buffer[-10:] # Last 10 messages please

    def errReceived(self, data):
        print "Error: %s" % data


# http://autobahn.ws/python
class WebSocketProcessOutputterThing(WebSocketServerProtocol):
    def onOpen(self):
        self.factory.register(self)
        for line in self.factory.process.buffer:
            self.sendMessage(line)

    def connectionLost(self, reason):
        WebSocketServerProtocol.connectionLost(self, reason)
        #super(WebSocketProcessOutputterThing, self).connectionLost(self, reason)
        self.factory.unregister(self)


class WebSocketProcessOutputterThingFactory(WebSocketServerFactory):
    protocol = WebSocketProcessOutputterThing
        
    def __init__(self, *args, **kwargs):
        WebSocketServerFactory.__init__(self, *args, **kwargs)
        #super(WebSocketProcessOutputterThingFactory, self).__init__(self, *args, **kwargs)
        self.clients = []
        self.process = ProcessProtocol(self)
        reactor.spawnProcess(self.process,COMMAND_NAME, COMMAND_ARGS, {})

    def register(self, client):
        msg("Registered client %s" % client)
        if not client in self.clients:
            self.clients.append(client)

    def unregister(self, client):
        msg("Unregistered client %s" % client)
        if client in self.clients:
            self.clients.remove(client)

    def broadcast(self, message):
        for client in self.clients:
            client.sendMessage(message)


if __name__ == "__main__":
    print "Running process %s with args %s" % (COMMAND_NAME, COMMAND_ARGS)
    factory = WebSocketProcessOutputterThingFactory("ws://%s:9000" % ("localhost" if LOCAL_ONLY else "0.0.0.0"), debug=False)
    listenWS(factory)
    reactor.run()
