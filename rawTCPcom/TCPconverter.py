#!/usr/bin/env python3

import asyncio
import time
import json
import uuid
import datetime
import sys
import collections
##import copy
import os

from socket import socket, SO_REUSEADDR, SOL_SOCKET
from asyncio import Task, coroutine, get_event_loop

from autobahn.asyncio import wamp, websocket
from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner 



class WampComponent(wamp.ApplicationSession):
    """WAMP application session for OTOne (Overrides protocol.ApplicationSession - WAMP endpoint session)
    """

    def onConnect(self):
        """Callback fired when the transport this session will run over has been established.
        """
        print(datetime.datetime.now(),' - TCP translator : WampComponent.onConnect:')
        self.join(u"ot_realm")


    @asyncio.coroutine
    def onJoin(self, details):
        """Callback fired when WAMP session has been established.

        May return a Deferred/Future.

        Starts instatiation of robot objects by calling :meth:`otone_client.instantiate_objects`.
        """
        print(datetime.datetime.now(),' - TCP translator : WampComponent.onJoin:')
        print('\n\targs: ',locals(),'\n')
        if not self.factory._myAppSession:
            self.factory._myAppSession = self
        try:
            self.factory._crossbar_connected = True
        except AttributeError:
            print('ERROR: factory does not have "crossbar_connected" attribute')


        def handshake(client_data):
            """Hook for factory to call _handshake()
            """
            print(datetime.datetime.now(),' - TCP-translator : WampComponent.handshake:')
            print('\n\targs: ',locals(),'\n')
##            # send handshake response to TCP
##            try:
##                self.factory._fwdMessage(client_data)
##            except AttributeError:
##                print('ERROR: factory does not have "_fwdMessage" attribute')

            # extract variables/information from handshake    
            try:
                self.factory._handshake(client_data)
            except AttributeError:
                print('ERROR: factory does not have "_handshake" attribute')


        def fwdMessage(client_data):
            """Hook for factory to call _fwdMessage()
            """
            print(datetime.datetime.now(),' - TCP-translator : WampComponent.called my name:')
            print('\n\targs: ',locals(),'\n')
            try:
                self.factory._fwdMessage(client_data)
            except AttributeError:
                print('ERROR: factory does not have "_fwdMessage" attribute')
            

            
##        Maybe put this back in if we want this to do something other than just pass messages
##        def dispatch_message(client_data):
##            """Hook for factory to call dispatch_message()
##            """
##            print(datetime.datetime.now(),' - TCP translator : WampComponent.dispatch_message:')
##            print('\n\targs: ',locals(),'\n')
##            try:
##                self.factory._dispatch_message(client_data)
##            except AttributeError:
##                print('ERROR: factory does not have "_dispatch_message" attribute')

        # subscribe to messages to TCP client and frontend        
        selfName = 'com.opentrons.'+self.outer.id
        print(datetime.datetime.now(),' - TCP-translator : client name: {}'.format(selfName))
        yield from self.subscribe(fwdMessage, selfName)
        yield from self.subscribe(handshake, 'com.opentrons.frontend')
        

    def onLeave(self, details):
        """Callback fired when WAMP session has been closed.
        :param details: Close information.
        """
        print('TCP translator : WampComponent.onLeave:')
        print('\n\targs: ',locals(),'\n')
        if self.factory._myAppSession == self:
            self.factory._myAppSession = None
        try:
            self.disconnect()
        except:
            raise
        

    def onDisconnect(self):
        """Callback fired when underlying transport has been closed.
        """
        print(datetime.datetime.now(),' - TCP translator : WampComponent.onDisconnect:')
        asyncio.get_event_loop().stop()
        crossbar_connected = False
        try:
            self.factory._crossbar_connected = False
        except AttributeError:
            print('ERROR: outer does not have "crossbar_connected" attribute')


class TCPtranslator():

    def __init__(self,loop):
        #__init__ VARIABLES FROM HARNESS
        print(datetime.datetime.now(),' - TCPtranslator.__init__:')
        print('\n\targs: ',locals(),'\n')
##        self.driver_dict = {}
##        self.meta_dict = {
##            'drivers' : lambda from_,session_id,name,param: self.drivers(from_,session_id,name,param),
##            'add_driver' : lambda from_,session_id,name,param: self.add_driver(from_,session_id,name,param),
##            'remove_driver' : lambda from_,session_id,name,param: self.remove_driver(from_,session_id,name,param),
##            'callbacks' : lambda from_,session_id,name,param: self.callbacks(from_,session_id,name,param),
##            'meta_callbacks' : lambda from_,session_id,name, param: self.meta_callbacks(from_,session_id,name,param),
##            'set_meta_callback' : lambda from_,session_id,name,param: self.set_meta_callback(from_,session_id,name,param),
##            'add_callback' : lambda from_,session_id,name,param: self.add_callback(from_,session_id,name,param),
##            'remove_callback' : lambda from_,session_id,name,param: self.remove_callback(from_,session_id,name,param),
##            'flow' : lambda from_,session_id,name,param: self.flow(from_,session_id,name,param),
##            'clear_queue' : lambda from_,session_id,name,param: self.clear_queue(from_,session_id,name,param),
##            'connect' : lambda from_,session_id,name,param: self.driver_connect(from_,session_id,name,param),
##            'disconnect' : lambda from_,session_id,name,param: self.driver_disconnect(from_,session_id,name,param),
##            'commands' : lambda from_,session_id,name,param: self.commands(from_,session_id,name,param),
##            'configs' : lambda from_,session_id,name,param: self.configs(from_,session_id,name,param),
##            'set_config' : lambda from_,session_id,name,param: self.set_config(from_,session_id,name,param),
##            'meta_commands' : lambda from_,session_id,name,param: self.meta_commands(from_,session_id,name,param)
##        }

##        self.in_dispatcher = {
##            'command': lambda from_,session_id,data: self.send_command(from_,session_id,data),
##            'meta': lambda from_,session_id,data: self.meta_command(from_,session_id,data)
##        }

        self.topic = {
            'frontend' : 'com.opentrons.frontend',
            'driver' : 'com.opentrons.driver',
            'labware' : 'com.opentrons.labware',
            'bootstrapper' : 'com.opentrons.bootstrapper'
        }

##        self.clients = {
##            # uuid : 'com.opentrons.[uuid]'
##        }
##        self.max_clients = 4

        self.id = str(uuid.uuid4())

        self.session_factory = wamp.ApplicationSessionFactory()
        self.session_factory.session = WampComponent
        self.session_factory._myAppSession = None
        self.session_factory._crossbar_connected = False
        self.transport_factory = None

        self.transport = None
        self.protocol = None

        self.loop = loop

        self.driverID =''

        self.session_factory.session.outer = self

        

##    Maybe put this back in if we want this to do something other than just pass messages
##    def dispatch_message(self, message):
##        print(datetime.datetime.now(),' - TCPtranslator.dispatch_message:')
##        print(datetime.datetime.now(),' - does nothing for now')
##        #print('\n\targs: ',locals(),'\n')
##        try:
##            dictum = collections.OrderedDict(json.loads(message.strip(), object_pairs_hook=collections.OrderedDict))
##            if 'type' in dictum and 'from' in dictum and 'sessionID' in dictum and 'data' in dictum:
##                if dictum['type'] in self.in_dispatcher:
##                    if self.client_check(dictum['from'],dictum['sessionID']):
##                        #opportunity to filter, not actually used
##                        self.in_dispatcher[dictum['type']](dictum['from'],dictum['sessionID'],dictum['data'])
##                    else:
##                        self.in_dispatcher[dictum['type']](dictum['from'],dictum['sessionID'],dictum['data'])
##                else:
##                    print(datetime.datetime.now(),' - ERROR:\n\r',sys.exc_info())
##                    print('type: ',dictum['type'])
##            else:
##                print(datetime.datetime.now(),' - ERROR:\n\r',sys.exc_info())
##                
##        except:
##            print(datetime.datetime.now(),' - ERROR:\n\r',sys.exc_info())
##
##
    def handshake(self, data):
        print(datetime.datetime.now(),' - TCPtranslator.handshake:')
        #print('\n\targs: ',locals(),'\n')

        data_dict = json.loads(data)
        if isinstance(data_dict, dict):
            if data_dict['to']== self.id:
                if 'message' in data_dict['data']:
                    print(' data has msg ')
                    if 'result' in data_dict['data']['message']:
                        print('message has result')
                        if data_dict['data']['message']['result']=='success':
                            print(' handshake sucessfull!')
                            print('set given id from driver')
##                            self.id = data_dict['sessionID']
                            self.topic['self'] = 'com.opentrons.'+self.id
                            self.driverID = data_dict['from']
                            msg = {'time':str(datetime.datetime.now()), 'type':'TCP handshake','to':self.id,'from':'com.opentrons.tcpRelay',
                               'sessionID':self.id,'data':{'name':'TCP relay','message':{'result':'success'}}}
                            self.fwdMessage(json.dumps(msg))

                            #send raw message from driver as well
                            self.fwdMessage(data)

                            #then shake hands---because?
                            print('Shake hands (just because it is nice?)')
                            self.publish('com.opentrons.driver_handshake','driver',self.id,'handshake','TCP comm','shake','true')

                        elif data_dict['data']['message']['result']=='already_connected':
                            msg = {'time':str(datetime.datetime.now()), 'type':'TCP handshake','to':self.id,'from':'com.opentrons.tcpRelay',
                               'sessionID':self.id,'data':{'name':'TCP relay','message':{'result':'already_connected'}}}
                            self.fwdMessage(json.dumps(msg))

                            #send raw message from driver as well
                            self.fwdMessage(data)
                        else:
                            print(datetime.datetime.now(),' - TCPtranslator.handshake: FAILED')
                            # told that handshake failed from driver
                            msg = {'time':str(datetime.datetime.now()), 'type':'TCP handshake','to':self.id,'from':'com.opentrons.tcpRelay',
                               'sessionID':self.id,'data':{'name':'TCP relay','message':{'result':'failed'}}}
                            self.fwdMessage(json.dumps(msg))

                            #send raw message from driver as well
                            self.fwdMessage(data)
                    else:
                        print(datetime.datetime.now(),' - TCPtranslator.handshake: ERROR - no handshake result')
                        # error in handshake method
                        msg = {'time':str(datetime.datetime.now()), 'type':'TCP handshake','to':self.id,'from':'com.opentrons.tcpRelay',
                           'sessionID':self.id,'data':{'name':'TCP relay','message':{'result':'ERROR'}}}
                        self.fwdMessage(json.dumps(msg))

                        #send raw message from driver as well
                        self.fwdMessage(data)
                else:
                    print(datetime.datetime.now(),' - TCPtranslator.handshake: ERROR - no handshake message')
                    # error in handshake method
                    msg = {'time':str(datetime.datetime.now()), 'type':'TCP handshake','to':self.id,'from':'com.opentrons.tcpRelay',
                       'sessionID':self.id,'data':{'name':'TCP relay','message':{'result':'ERROR'}}}
                    self.fwdMessage(json.dumps(msg))

                    #send raw message from driver as well
                    self.fwdMessage(data)
            else:
                print('reading message to other clients (i.e. web interface)')
        else:
            print('data is not dict')
            
            
    def fwdMessage(self, data):
        print(datetime.datetime.now(),' - TCPtranslator.fwdMessage:')
        data_dict = json.loads(data)
        if isinstance(data_dict, dict):
##            # get data
##            dataVals = data_dict['data']
            try:
##                dataStr = json.dumps(dataVals)
##                self.relay.passMsg(dataStr,data_dict['to'])
                dataStr = json.dumps(data_dict)
                self.relay.passMsg(data,data_dict['to'])
            except:
                print('error passing message')
        else:
            print('data is not dict')

    def publish(self,topic,to,session_id,type_,name,message,param):
        """
        """
        print(datetime.datetime.now(),' - TCPtranslator.publish:')
        #print('\n\targs: ',locals(),'\n')
        if self.session_factory is not None and topic is not None and type_ is not None:
            if name is None:
                name = 'None'
            if message is None:
                message = ''
            if param is None:
                param = ''
            if self.session_factory is not None:
                if self.session_factory._myAppSession is not None:
                    time_string = str(datetime.datetime.now())
                    msg = {'time':time_string, 'type':type_,'to':to,'from':self.id,'sessionID':session_id,'data':{'name':name,'message':{message:param}}}
                    try:
                        if topic in self.topic:
                            print('TOPIC: ',self.topic)
                            print(datetime.datetime.now(),'url topic: ',self.topic.get(topic))
                            self.session_factory._myAppSession.publish(self.topic.get(topic),json.dumps(msg))
##                        elif topic in self.clients:
##                            print('TO: ',to)
##                            url_topic = 'com.opentrons.'+to
##                            print(datetime.datetime.now(),'url topic: ',url_topic)
##                            self.session_factory._myAppSession.publish(self.clients.get(topic),json.dumps(msg))
                        elif topic == 'com.opentrons.driver_handshake':
                            print('TOPIC: ',topic)
                            print(datetime.datetime.now(),'url topic: ',topic)
                            self.session_factory._myAppSession.publish(topic,json.dumps(msg))
                    except:
                        print(datetime.datetime.now(),' - Error:\n\r',sys.exc_info())
            else:
                print(datetime.datetime.now(),' - Error: caller._myAppSession is None')
        else:
            print(datetime.datetime.now(),' - Error: calller, topic, or type_ is None')



    def _make_connection(self, url_protocol='ws', url_domain='0.0.0.0', url_port=8080, url_path='ws', debug=False, debug_wamp=False):
        print(datetime.datetime.now(),' - TCPtranslator._make_connection:')
        #print('\n\targs: ',locals(),'\n')
        if self.loop.is_running():
            print('self.loop is running. stopping loop now')
            self.loop.stop()
        print(self.transport_factory)
        coro = self.loop.create_connection(self.transport_factory, url_domain, url_port)
        self.transport, self.protocol = self.loop.run_until_complete(coro)
        #protocoler.set_outer(self)
        if not self.loop.is_running():
            print('about to call self.loop.run_forever()')
            self.loop.run_forever()


    def connect(self, url_protocol='ws', url_domain='0.0.0.0', url_port=8080, url_path='ws', debug=False, debug_wamp=False, keep_trying=True, period=5):
        print(datetime.datetime.now(),' - TCPtranslator.connect:')
        print('\n\targs: ',locals(),'\n')
        if self.transport_factory is None:
            url = url_protocol+"://"+url_domain+':'+str(url_port)+'/'+url_path

            self.transport_factory = websocket.WampWebSocketClientFactory(self.session_factory,
                                                                            url=url,
                                                                            debug=debug,
                                                                            debug_wamp=debug_wamp)

        self.session_factory._publish = self.publish
        self.session_factory._handshake = self.handshake
        self.session_factory._fwdMessage= self.fwdMessage
##        self.session_factory._dispatch_message = self.dispatch_message

        if not keep_trying:
            try:
                print('\nDriver attempting crossbar connection\n')
                self._make_connection(url_domain=url_domain, url_port=url_port)
            except:
                print('crossbar connection attempt error:\n',sys.exc_info())
                pass
        else:
            while True:
                while (self.session_factory._crossbar_connected == False):
                    try:
                        print('\nDriver attempting crossbar connection\n')
                        self._make_connection(url_domain=url_domain, url_port=url_port)
                    except KeyboardInterrupt:
                        self.session_factory._crossbar_connected = True
                    except:
                        print('crossbar connection attempt error:\n',sys.exc_info())
                        pass
                    finally:
                        print('\nDriver connection failed, sleeping for 5 seconds\n')
                        time.sleep(period)
            

    def disconnect(self):
        print(datetime.datetime.now(),' - TCPtranslator.disconnect:')
        self.transport.close()
        self.transport_factory = None




###  This was mostly based off of the github gregvish/chat.py code

class Peer(object):
    def __init__(self, server, sock, name):
        self.loop = server.loop
        self.name = name
        self._sock = sock
        self._server = server
        self.id = self._server._translator.id

        print(datetime.datetime.now(),' - rawTcpServer: start listening for TCP message:')
        Task(self._peer_handler())

    def send(self, data):
        return self.loop.sock_sendall(self._sock, data.encode('utf8'))
    
    @coroutine
    def _peer_handler(self):
        try:
            yield from self._peer_loop()
        except IOError:
            pass
        finally:
            self._server.remove(self)

    @coroutine
    def _peer_loop(self):
        while True:
            buf = yield from self.loop.sock_recv(self._sock, 400000)
            print(datetime.datetime.now(),' - rawTcpServer: msg from TCP client received:')
            if buf == b'':
                break
            
            # decode and remove delimiter
            buffOut = buf.decode('utf8')
            cleanMsg = buffOut.strip('\n\r')
            print(cleanMsg)
            rawtojson = json.loads(cleanMsg)

            # send message over to crossbar.io
            print(datetime.datetime.now(),' - rawTcpServer: sending TCP message to crossbar')
            self._server._translator.publish(rawtojson['topic'],self._server._translator.driverID,
                                             self.id,rawtojson['type'],
                                             rawtojson['name'],rawtojson['message'],rawtojson['param'])
    
class rawTcpServer(object):
    def __init__(self, loop, port, translator):
        print(datetime.datetime.now(),' - rawTcpServer: Initalize the TCP server')
        self.loop = loop
        self._serv_sock = socket()
        self._serv_sock.setblocking(0)
        self._serv_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self._serv_sock.bind(('',port))
        # only allow one TCP client to connect
        self._serv_sock.listen(0)
        self._peers = []
        self._translator = translator
        Task(self._server())

    def remove(self, peer):
        self._peers.remove(peer)
        print(datetime.datetime.now(),' - rawTcpServer.Client disconnected:')
        # Is there a way to tell the driver that it is disconnected?
##        self.broadcast('%s\tquit!\n\r' % (peer.global_name,))

    def broadcast(self, message):
##        print(list(self._peers))
        print(datetime.datetime.now(),' - rawTcpServer: Passing message to All -- may not need')
        print("TCP Server: sending msg")
        print(message)
        for peer in self._peers:
            peer.send(message)


##    def relay(self, message, incomingSock):
####        print(list(set(incomingSock)-set(self._peers)))
##        
##        for peer in self._peers:
##            if peer._sock != incomingSock:
##                peer.send(message)

    def passMsg(self, msg, peer_id):
        print(datetime.datetime.now(),' - rawTcpServer: Passing message to TCP Client')
        msgOut = msg + '\n\r'
        for peer in self._peers:
            if peer.id == peer_id:
                peer.send(msgOut)

                
    @coroutine
    def _server(self):
        while True:
            peer_sock, peer_name = yield from self.loop.sock_accept(self._serv_sock)
            print(datetime.datetime.now(),' - rawTcpServer : New TCP Client connected')
            peer_sock.setblocking(0)
            peer = Peer(self, peer_sock, peer_name)
            self._peers.append(peer)
            
            # Extend handshake to driver_client
            print(datetime.datetime.now(),' - rawTcpServer : Handshake sent to driver')
            self._translator.publish('com.opentrons.driver_handshake',self._translator.driverID,self._translator.id,'handshake','driver','extend','true')

            # Tell client that handshake has been initialized
            time_string = str(datetime.datetime.now())
            msg = {'time':time_string, 'type':'TCP handshake','to':self._translator.id,'from':'com.opentrons.tcpRelay',
                   'sessionID':self._translator.id,'data':{'name':'TCP relay','message':{'Start-up':'initalized'}}}
            delimMsg = json.dumps(msg) + '\n\r'
            print(datetime.datetime.now(),' - rawTcpServer : TCP client sent initialization message')
            print(delimMsg.encode())
            peer.send(delimMsg)



if __name__ == '__main__':

    try:

        # INITIAL SETUP
        print('\nBEGIN INIT...\n')

        # get asyncio event loop
        loop = get_event_loop()

        
        print(datetime.datetime.now(),' - INITIAL SETUP - Autobahn/Crossbar.io connection setup ','* * '*10)
        TCP_trans = TCPtranslator(loop)

        # START RAW TCP SERVER
        serverPort = 7887
        relayServer = rawTcpServer(loop, serverPort, TCP_trans)

        # point to relay server for TCP translator
        TCP_trans.relay = relayServer

        print('END INIT')


        print(datetime.datetime.now(),' - Connect to crossbar.io ','* * '*10)
        TCP_trans.connect(
            url_domain= '0.0.0.0',
            url_port=8080
            )

    except KeyboardInterrupt:
        pass
    finally:
        print('disconnect')
        TCP_trans.disconnect()
        print('ALL DONE!')














