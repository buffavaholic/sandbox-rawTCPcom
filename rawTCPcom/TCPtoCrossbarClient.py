#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Created on Fri Apr 24 15:11:09 2015

@author: Randy

This is the main module of the OTOne Python backend code. When started, it creates 
a publisher (:class:`publisher.Publisher`) and a subscriber (:class:`subscriber.Subscriber`)
for handling all communication with a WAMP router and then tries to make a connection 
(:meth:`otone_client.make_a_connection`) with the Crossbar.io WAMP router. Once that 
connection is established, it instantiates and configures various objects with 
:meth:`otone_client.instantiate_objects`:
 
 head: :class:`head.Head` - Represents the robot head and creates a connection with Smoothieboard
 
 deck: :class:`deck.Deck` - Represents the robot deck

 runner: :class:`protocol_runner.ProtocolRunner` - Runs protocol jobs

 the_sk: :class:`script_keeper.ScriptKeeper` - Handles shell scripts


"""

#import RobotLib
import json, asyncio, sys, time, collections, os, sys, shutil

from head import Head
from deck import Deck

##from robot_to_tcp_subscriber import TCP_subscriber
from publisher import Publisher

from file_io import FileIO
from ingredients import Ingredients

from protocol_runner import ProtocolRunner

import script_keeper as sk
from script_keeper import ScriptKeeper


debug = True
verbose = False

#VARIABLES

#declare globol objects here
head = None
deck = None
runner = None
subscriber = None
publisher = None
def_start_protocol = None
client_status = False
crossbar_status = False

if debug == True: FileIO.log('starting up')
#for testing purposes, read in a protocol.json file
path = os.path.abspath(__file__)
dir_path = os.path.dirname(path)
dir_par_path = os.path.dirname(dir_path)
dir_par_par_path = os.path.dirname(dir_par_path)
fname_default_protocol = os.path.join(dir_path,'data/sample_user_protocol.json')
fname_default_containers = os.path.join(dir_path, 'data/containers.json')
fname_default_calibrations = os.path.join(dir_path, 'data/pipette_calibrations.json')
fname_data = os.path.join(dir_par_par_path,'otone_data')
fname_data_containers = os.path.join(dir_par_par_path,'otone_data/containers.json')
fname_data_calibrations = os.path.join(dir_par_par_path, 'otone_data/pipette_calibrations.json')
print('dir_path: ', dir_path)
print('dir_par_path: ', dir_par_path)
print('dir_par_part_path: ', dir_par_par_path)
print('fname_data: ', fname_data)
print('fname_default_containers: ', fname_default_containers)
print('fname_data_containers: ', fname_data_containers)


if not os.path.isdir(fname_data):
    os.makedirs(fname_data)
#if not os.path.exists(fname_data_containers):
open(fname_data_containers,"w+")
shutil.copy(fname_default_containers, fname_data_containers)

if not os.path.exists(fname_data_calibrations):
    open(fname_data_calibrations,"w+")
    shutil.copy(fname_default_calibrations, fname_data_calibrations)

prot_dict = FileIO.get_dict_from_json(fname_default_protocol)

clients = {}
clients_list ={}
#Import and setup autobahn WAMP peer
from autobahn.asyncio import wamp, websocket

class WampComponent(wamp.ApplicationSession):
    """WAMP application session for OTOne (Overrides protocol.ApplicationSession - WAMP endpoint session)
    """

    def onConnect(self):
        """Callback fired when the transport this session will run over has been established.
        """
        self.join(u"ot_realm")

    @asyncio.coroutine
    def onJoin(self, details):
        """Callback fired when WAMP session has been established.

        May return a Deferred/Future.

        Starts instatiation of robot objects by calling :meth:`otone_client.instantiate_objects`.
        """
        if debug == True: FileIO.log('ecg_client : WampComponent.onJoin called')
        if not self.factory._myAppSession:
            self.factory._myAppSession = self
        
        crossbar_status = True    
        #instantiate_objects()
        
        
        def set_client_status(status):
            if debug == True: FileIO.log('ecg_client : WampComponent.set_client_status called')
            global client_status
            client_status = status
            #self.publish('com.opentrons.robot_to_browser',True)
            #FileIO.log('ecg_client : made it past publish?')
            self.publish('com.opentrons.ecg_ready',True)

        self.subscribe('com.opentrons.robot_ready')
        FileIO.log('about to publish com.ecg.client_ready TRUE')
        self.publish('com.opentrons.browser_ready',True)
        self.publish('com.opentrons.robot_to_browser',True)
        #self.publish('com.opentrons.browser_to_robot','home')
        #yield from self.subscribe(set_client_status, 'com.opentrons.robot_ready')
##        subscriber.dispatch_message("test")
        #yield from self.subscribe(set_client_status, 'com.opentrons.robot_to_browser')
        yield from self.subscribe(subscriber.dispatch_message, 'com.opentrons.robot_to_browser')
        #yield from self.subscribe(subscriber.dispatch_message, 'com.opentrons.browser_to_robot')

##        self.publish('com.opentrons.browser_to_robot',json.dumps({
##    'type' : 'home',
##    'data': 'y'
##  }))
##        input("wait to do next thing")
        self.publish('com.opentrons.browser_to_robot',json.dumps({
    'type' : 'home',
    'data': {'x':'true', 'y':'true', 'z':'true', 'a':'true'}
  }))
##        input("wait to do next thing")
##        self.publish('com.opentrons.browser_to_robot',json.dumps({
##    'type' : 'raw',
##    'data': 'G0 X50'
##  }))

##    @asyncio.coroutine
##    def txMsg(self, msg):
##        input("wait to do next thing")
##        self.publish('com.opentrons.browser_to_robot',json.dumps({
##    'type' : 'home',
##    'data': 'x'
##  }))
        
    def onLeave(self, details):
        """Callback fired when WAMP session has been closed.
        
        :param details: Close information.
        """
        if self.factory._myAppSession == self:
            self.factory._myAppSession = None
        try:
            self.disconnect()
        except:
            pass
        
    def onDisconnect(self):
        """Callback fired when underlying transport has been closed.
        """
        asyncio.get_event_loop().stop()


def make_a_connection():
    """Attempt to create streaming transport connection and run event loop
    """
    coro = loop.create_connection(transport_factory, '127.0.0.1', 8080)

    transporter, protocoler = loop.run_until_complete(coro)
    #instantiate the subscriber and publisher for communication
    
    loop.run_forever()

def passMsg(msg):
    print("in pass message")
    print(msg)
##    session_factory._myAppSession.publish('com.opentrons.browser_to_robot','{"type" : "home","data": "y"}')
    session_factory._myAppSession.publish('com.opentrons.browser_to_robot',msg)
    #asyncio.Task(session_factory.session.txMsg(session_factory.session,msg))
    #yield from tcpMsgOut(msg)

class TCP_subscriber():
    """Subscribes to messages from WAMP Router on 'com.opentrons.browser_to_robot' and dispatches commands according to the :obj:`dispatcher` dictionary.

    
    The Subscriber class is intended to be intantiated into a subscriber object
    to dispatch commands from the GUI and ProtocolRunner to the appropriate object(s)
    for robot actions.

    The subscriber object holds references to all the relevant objects such
    as the head, queue objects etc.

    
    :dispatcher:
    * 'home' : lambda self, data: self.home(data),
    * 'stop' : lambda self, data: self.head.theQueue.kill(data),
    * 'reset' : lambda self: self.reset(),
    * 'move' : lambda self, data: self.head.move(data),
    * 'step' : lambda self, data: self.head.step(data),
    * 'calibratePipette' : lambda self, data: self.calibrate_pipette(data),
    * 'calibrateContainer' : lambda self, data: self.calibrate_container(data),
    * 'getCalibrations' : lambda self: self.get_calibrations(),
    * 'saveVolume' : lambda self, data: self.head.save_volume(data),
    * 'movePipette' : lambda self, data: self.move_pipette(data),
    * 'movePlunger' : lambda self, data: self.move_plunger(data),
    * 'speed' : lambda self, data: self.speed(data),
    * 'createDeck' : lambda self, data: self.create_deck(data),
    * 'instructions' : lambda self, data: self.instructions(data),
    * 'infinity' : lambda self, data: self.infinity(data),
    * 'pauseJob' : lambda self: self.head.theQueue.pause_job(),
    * 'resumeJob' : lambda self: self.head.theQueue.resume_job(),
    * 'eraseJob' : lambda self: self.runner.insQueue.erase_job(),
    * 'raw' : lambda self, data: self.head.raw(data),
    * 'update' : lambda self, data: self.loop.create_task(self.update(data)),
    * 'wifimode' : lambda self, data: self.wifi_mode(data),
    * 'wifiscan' : lambda self, data: self.wifi_scan(data),
    * 'hostname' : lambda self, data: self.change_hostname(data),
    * 'poweroff' : lambda self: self.poweroff(),
    * 'reboot' : lambda self: self.reboot(),
    * 'shareinet': lambda self: self.loop.create_task(self.share_inet()),
    * 'restart' : lambda self: self.restart()

    :todo:
    - clean up inclusion of head and runner objects -> referenced by dispatch
    - move publishing into respective objects and have those objects use :class:`publisher` a la :meth:`get_calibrations` (:meth:`create_deck`, :meth:`wifi_scan`)
    


    """
    
#Special Methods
    def __init__(self, session,loop):
        """Initialize Subscriber object
        """
        if debug == True: FileIO.log('subscriber_ecg.__init__ called')
##        self.head = None
##        self.deck = None
##        self.runner = None
        self.caller = session
        self.loop = loop
        #self.wtf_mate("test")
##        self.dispatch_message("test")
        FileIO.log('subscriber_ecg.testing dispatch_message called')
        
    def __str__(self):
        return "Robot to TCP Subscriber"

    
    def dispatch_message(self, message):
        """The first point of contact for incoming messages.
        """

        if debug == True:
            FileIO.log('subscriber.dispatch_message called')
            if verbose == True: FileIO.log('\nmessage: ',message,'\n')
        #print('message type: ',type(message))
        if sys.getsizeof(message)<190000:
            
            try:
##                formMsg = message
##                bitMsg = formMsg.encode()
##                print(bitMsg)
                dictum = collections.OrderedDict(json.loads(message.strip(), object_pairs_hook=collections.OrderedDict))
                FileIO.log('\tdictum[type]: ',dictum['type'])
                if 'type' in dictum:
##                    if verbose == True:FileIO.log('\tdictum[data]:\n\n',json.dumps(dictum['data'],sort_keys=True,indent=4,separators=(',',': ')),'\n')
                    self.route(dictum['type'],dictum['data'])
                else:
                    self.route('other',bitMsg)
##                protoc.sendOnlyData(trans,bitMsg )
            except:
                FileIO.log('subscriber.dispatch_message couldnt send')
        else:
            FileIO.log('msg too long: {}'.format(sys.getsizeof(message)))
##        yield from return_msg(message)
##        except:
##            FileIO.log('subscriber.dispatch_message failed')

    def route(self, type_, data):
        """Dispatch commands according to :obj:`router` dictionary
        """
        if debug == True:
            FileIO.log('subscriber.route called')
            if verbose == True: FileIO.log('\n\n\ttype_: ',type_,'\n\tdata:',data,'\n')
        
        if verbose == True:FileIO.log('\tdictum[string]: ',json.dumps(data['string'],sort_keys=True,indent=4,separators=(',',': ')),'\n')
        try:
            if type_ in self.router:
                FileIO.log('subscriber.route about to pass data')
##                dictum_route = collections.OrderedDict(json.loads(data.strip(), object_pairs_hook=collections.OrderedDict))
##                for k in data.items():
##                    print(k)
                self.router[type_](self,data)
            else:
                type_='other'
                self.router[type_](self,data)
##            if 'string' in dictum_route:
##                if data is not None:
##                    self.router[type_](self,dictum_route['string'])
##                else:
##                    FileIO.log('subscriber.route no string data')
####                    self.dispatcher[type_](self)
##            else:
##                FileIO.log('subscriber.route no string type')
        except:
            FileIO.log('subscriber.route couldnt route')

    def smoothie_rpt(self, data):
        if debug == True & verbose == True: FileIO.log('subscriber.route smoothie called')
        bitMsg = data
##        bitMsg = data.encode()
##        protoc.sendOnlyData(trans,bitMsg)

    def status(self, data):
        if debug == True & verbose == True: FileIO.log('subscriber.route status called')
##        getStr = json.dumps(data['string'],sort_keys=True,indent=4,separators=(',',': '))
        getStr = json.dumps(data['string'],sort_keys=True,separators=(',',': '))
        bitMsg = getStr.encode()
        protoc.sendOnlyData(trans,bitMsg)

    def pos(self, data):
        if debug == True & verbose == True: FileIO.log('subscriber.route pos called')
##        getStr = json.dumps(data['string'],sort_keys=True,indent=4,separators=(',',': '))
        getStr = json.dumps(data['string'],sort_keys=True,separators=(',',': '))
        bitMsg = getStr.encode()
        protoc.sendOnlyData(trans,bitMsg)

    def raw_response(self, data):
        if debug == True & verbose == True: FileIO.log('subscriber.route other called')
##        bitMsg = data.encode()
        try:
            getStr = json.dumps(data,sort_keys=True,separators=(',',': '))
            bitMsg = getStr.encode()
            protoc.sendOnlyData(trans,bitMsg)
        except:
            protoc.sendOnlyData(trans,data)

    def wholeJSON(self, data):
        if debug == True & verbose == True: FileIO.log('subscriber.route whole JSON called')
        
        getStr = json.dumps(data,sort_keys=True,separators=(',',': '))
        bitMsg = getStr.encode()
        FileIO.log('size of containers: {}'.format(sys.getsizeof(bitMsg )))
        protoc.sendOnlyData(trans,bitMsg)
        
        
    # make a dict to pass messages to the raw TCP
    router = {'smoothie'  : lambda self, data: self.smoothie_rpt(data),
              'status'    : lambda self, data: self.status(data),
              'position'  : lambda self, data: self.pos(data),
              'other'     : lambda self, data: self.raw_response(data),
              'containers': lambda self, data: self.wholeJSON(data)
              }
##              'containerLocations': lambda self, data: self.wholeJSON(data)
##              }
    #instantiate/activate the dispatcher/router dictionary
    #create Dispatcher dictionary object which is the equivalent of the
    #previous socketHandlers object in js code
##    dispatcher = {'home' : lambda self, data: self.home(data),
##              'stop' : lambda self, data: self.head.theQueue.kill(data),
##              'reset' : lambda self: self.reset(),
##              'move' : lambda self, data: self.head.move(data),
##              'step' : lambda self, data: self.head.step(data),
##              'calibratePipette' : lambda self, data: self.calibrate_pipette(data),  #needs xtra code
##              'calibrateContainer' : lambda self, data: self.calibrate_container(data),
##              'getCalibrations' : lambda self: self.get_calibrations(),
##              'saveVolume' : lambda self, data: self.head.save_volume(data),
##              'movePipette' : lambda self, data: self.move_pipette(data),#needs xtra code
##              'movePlunger' : lambda self, data: self.move_plunger(data),
##              'speed' : lambda self, data: self.speed(data),          #needs xtra code
##              'getContainers' : lambda self: self.get_containers(),
##              'createDeck' : lambda self, data: self.create_deck(data),#needs xtra code
##              'configureHead' : lambda self, data: self.configure_head(data),
##              'relativeCoords' : lambda self: self.head.relative_coords(),
##              'instructions' : lambda self, data: self.instructions(data),#needs xtra code
##              'infinity' : lambda self, data: self.infinity(data),
##              'pauseJob' : lambda self: self.head.theQueue.pause_job(),
##              'resumeJob' : lambda self: self.head.theQueue.resume_job(),
##              'eraseJob' : lambda self: self.runner.insQueue.erase_job(),
##              'raw' : lambda self, data: self.head.raw(data),
##              'update' : lambda self, data: self.loop.create_task(self.update(data)),
##              'wifimode' : lambda self, data: self.wifi_mode(data),
##              'wifiscan' : lambda self, data: self.wifi_scan(data),
##              'hostname' : lambda self, data: self.change_hostname(data),
##              'poweroff' : lambda self: self.poweroff(),
##              'reboot' : lambda self: self.reboot(),
##              'shareinet': lambda self: self.loop.create_task(self.share_inet()),
##              'restart' : lambda self: self.restart(),
##              'containerDepthOverride': lambda self, data: self.container_depth_override(data)
##              }
    


# Client to send data to the raw TCP/IP router
class EchoClient(asyncio.Protocol):
    message = 'Client Echo \n\r'

    def connection_made(self, transport):
        transport.write(self.message.encode())
        print('data sent: {}'.format(self.message))

    def data_received(self, data):
        msgIn = data.decode()
        splitMsg = msgIn.split('\t')
        if debug == True: FileIO.log('message in from:',splitMsg[0],'\n msg:',splitMsg[1])
##        print('data received: {}'.format(data.decode()))
        if splitMsg[0] == 'com.opentrons.robot_to_tcp':
            if debug == True: FileIO.log('message from self')            
        else:
            if debug == True: FileIO.log('message not from self')
            passMsg(splitMsg[1])

    def connection_lost(self, exc):
        print('server closed the connection')
        asyncio.get_event_loop().stop()

##    @asyncio.coroutine    
    def sendOnlyData(self, transport, data):
        formatData = data.decode()+'\n\r'
        FileIO.log('data sent out-------')
##        print('data sent out: {}'.format(formatData))
        transport.write(formatData.encode())
        
        

try:
    session_factory = wamp.ApplicationSessionFactory()
    session_factory.session = WampComponent

    session_factory._myAppSession = None

    url = "ws://127.0.0.1:8080/ws"
    transport_factory = websocket \
            .WampWebSocketClientFactory(session_factory,
                                        url=url,
                                        debug=False,
                                        debug_wamp=False)
    #SimpEcho = SimpleEchoProtocol()


    


    loop = asyncio.get_event_loop()
    coro = loop.create_connection(EchoClient, '127.0.0.1', 1234)
    trans, protoc = loop.run_until_complete(coro)
##    server = loop.run_until_complete(asyncio.start_server(add_send_task,'0.0.0.0',2345))
    
    
    #SimpEcho.robot = session_factory.session
    #serverProt = loop.create_server(SimpleEchoProtocol, '0.0.0.0',2345)
    
    #server=loop.run_until_complete(serverProt)

    
    
    subscriber = TCP_subscriber(session_factory, loop)
##    subscriber.dispatch_message("test")
    publisher = Publisher(session_factory)
    

    while (crossbar_status == False):
        try:
            FileIO.log('trying to make a connection...')
            make_a_connection()
        except KeyboardInterrupt:
            crossbar_status = True
        except:
            #raise
            pass
        finally:
            FileIO.log('error while trying to make a connection, sleeping for 5 seconds')
            time.sleep(5)
except KeyboardInterrupt:
    pass
finally:
    loop.close()




