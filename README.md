# sandbox-rawTCPcom
A module to be able to use raw TCP/IP communication with the Opentrons 
alpha backend

This code handles communication between the backend drivers of the 
Opentrons Liquid handler and any clients connecting via a raw TCP/IP 
websocket and not through autobahn/crossbar.io. This is done in 
TCPconverter.py which has two primary functions:

*[Raw TCP Server](#RawTCPServer)
*[Autobahn.ws Relay](#AutobahnwsRelay)


---
## Raw TCP Server:

This part, carried out by the rawTcpServer class and Peer subclass, 
which has 3 functions:

1. Start a TCP server and listen for incoming 
clients on port 7887 
2. When a client connects, send the client its ID 
number and then relay any incoming messages to the crossbar.io server 
using that ID 
3. Send any messages from crossbar addressed to that 
client ID back to the TCP client.

This sever is set up to send stringified json messages. *important* 
Currently the TCP client is expecting the '\n\r' delimiter, and chosen 
such that hopefully that delimiter wont be used in any messages. Also 
the client is terminating its outgoing messages with the same '\n\r' 
terminator so that is stripped off before sending to the crossbar.io 
server.


---
## Autobahn.ws Relay:
This part connects with the crossbar.io server on port 8080, does the 
initial handshake with com.opentrons.driver_handshake, passes messages 
from the TCP client to 'com.opentrons.driver' and sends any messages 
coming to the client ID back to the TCP client. This work is carried out 
by the TCPtranslator class. It is assumed that the messages coming from 
the TCP client are formatted how the driver_client is expecting as no 
re-formatting is done here.

---
## Requirements:

Because this code is based off of the 
opentrons/sandbox-driver/client_driver.py it requires autobahn v0.10.3

other modules:

* autobahn v0.10.3
* asyncio
* socket
* time
* json
* uuid
* datetime
* sys
* collections
* os

---
## To do:
- Add subscription to labware when that comes up 
- Maybe allow for multiple TCP clients to connect but since there is only one robot, I am 
not sure that is actually necessary.
