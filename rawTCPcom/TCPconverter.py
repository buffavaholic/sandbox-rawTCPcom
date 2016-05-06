#!/usr/bin/env python3

import asyncio
import time
import json
import uuid
import datetime
import sys
import collections
import copy
import os

##from smoothie_driver import SmoothieDriver

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
        print(datetime.datetime.now(),' - driver_client : WampComponent.onConnect:')
        self.join(u"ot_realm")


    @asyncio.coroutine
    def onJoin(self, details):
        """Callback fired when WAMP session has been established.

        May return a Deferred/Future.

        Starts instatiation of robot objects by calling :meth:`otone_client.instantiate_objects`.
        """
        print(datetime.datetime.now(),' - driver_client : WampComponent.onJoin:')
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
##            print(datetime.datetime.now(),' - TCP-translator : didnt do anything yet')
            try:
                self.factory._handshake(client_data)
            except AttributeError:
                print('ERROR: factory does not have "_handshake" attribute')
        def hearSelf(client_data):
            print(datetime.datetime.now(),' - TCP-translator : WampComponent.called my name:')
            print('\n\targs: ',locals(),'\n')

        def fwdMessage(client_data):
            print(datetime.datetime.now(),' - TCP-translator : WampComponent.called my name:')
            print(datetime.datetime.now(),' - TCP-translator : time to forward the message:')
            print('\n\targs: ',locals(),'\n')
            try:
                self.factory._fwdMessage(client_data)
            except AttributeError:
                print('ERROR: factory does not have "_fwdMessage" attribute')
            

            

##        def dispatch_message(client_data):
##            """Hook for factory to call dispatch_message()
##            """
##            print(datetime.datetime.now(),' - driver_client : WampComponent.dispatch_message:')
##            print('\n\targs: ',locals(),'\n')
##            try:
##                self.factory._dispatch_message(client_data)
##            except AttributeError:
##                print('ERROR: factory does not have "_dispatch_message" attribute')
        selfName = 'com.opentrons.'+self.outer.id
        print(selfName)
        yield from self.subscribe(fwdMessage, selfName)
        yield from self.subscribe(handshake, 'com.opentrons.frontend')
        print(datetime.datetime.now(),' about to publish to driver_handshake')
        time_string = str(datetime.datetime.now())
        msg = {'time':time_string, 'type':'com.opentrons.driver_handshake','to':'','from':self.outer.id,'sessionID':self.outer.id}
        self.publish('com.opentrons.driver_handshake',json.dumps(msg))
##        self.publish('com.opentrons.driver_handshake',"","",'handshake','driver','extend','')
        print('post publish')
##        yield from self.subscribe(hearSelf,  'com.opentrons.driver_handshake')
        
##        yield from self.subscribe(dispatch_message, 'com.opentrons.driver')
##        print('post yields')
##        handshake(json.dumps(msg))


    def onLeave(self, details):
        """Callback fired when WAMP session has been closed.
        :param details: Close information.
        """
        print('driver_client : WampComponent.onLeave:')
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
        print(datetime.datetime.now(),' - driver_client : WampComponent.onDisconnect:')
        asyncio.get_event_loop().stop()
        crossbar_connected = False
        try:
            self.factory._crossbar_connected = False
        except AttributeError:
            print('ERROR: outer does not have "crossbar_connected" attribute')


class TCPtranslator():

    def __init__(self,loop):
        #__init__ VARIABLES FROM HARNESS
        print(datetime.datetime.now(),' - DriverClient.__init__:')
        print('\n\targs: ',locals(),'\n')
        self.driver_dict = {}
        self.meta_dict = {
            'drivers' : lambda from_,session_id,name,param: self.drivers(from_,session_id,name,param),
            'add_driver' : lambda from_,session_id,name,param: self.add_driver(from_,session_id,name,param),
            'remove_driver' : lambda from_,session_id,name,param: self.remove_driver(from_,session_id,name,param),
            'callbacks' : lambda from_,session_id,name,param: self.callbacks(from_,session_id,name,param),
            'meta_callbacks' : lambda from_,session_id,name, param: self.meta_callbacks(from_,session_id,name,param),
            'set_meta_callback' : lambda from_,session_id,name,param: self.set_meta_callback(from_,session_id,name,param),
            'add_callback' : lambda from_,session_id,name,param: self.add_callback(from_,session_id,name,param),
            'remove_callback' : lambda from_,session_id,name,param: self.remove_callback(from_,session_id,name,param),
            'flow' : lambda from_,session_id,name,param: self.flow(from_,session_id,name,param),
            'clear_queue' : lambda from_,session_id,name,param: self.clear_queue(from_,session_id,name,param),
            'connect' : lambda from_,session_id,name,param: self.driver_connect(from_,session_id,name,param),
            'disconnect' : lambda from_,session_id,name,param: self.driver_disconnect(from_,session_id,name,param),
            'commands' : lambda from_,session_id,name,param: self.commands(from_,session_id,name,param),
            'configs' : lambda from_,session_id,name,param: self.configs(from_,session_id,name,param),
            'set_config' : lambda from_,session_id,name,param: self.set_config(from_,session_id,name,param),
            'meta_commands' : lambda from_,session_id,name,param: self.meta_commands(from_,session_id,name,param)
        }

        self.in_dispatcher = {
            'command': lambda from_,session_id,data: self.send_command(from_,session_id,data),
            'meta': lambda from_,session_id,data: self.meta_command(from_,session_id,data)
        }

        self.topic = {
            'frontend' : 'com.opentrons.frontend',
            'driver' : 'com.opentrons.driver',
            'labware' : 'com.opentrons.labware',
            'bootstrapper' : 'com.opentrons.bootstrapper'
        }

        self.clients = {
            # uuid : 'com.opentrons.[uuid]'
        }
        self.max_clients = 4

        self.id = str(uuid.uuid4())

        self.session_factory = wamp.ApplicationSessionFactory()
        self.session_factory.session = WampComponent
        self.session_factory._myAppSession = None
        self.session_factory._crossbar_connected = False
        self.transport_factory = None

        self.transport = None
        self.protocol = None

##        self.loop = asyncio.get_event_loop()
        self.loop = loop

        self.session_factory.session.outer = self

        


    def dispatch_message(self, message):
        print(datetime.datetime.now(),' - DriverClient.dispatch_message:')
        print(datetime.datetime.now(),' - does nothing for now')
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
        print(datetime.datetime.now(),' - DriverClient.handshake:')
        #print('\n\targs: ',locals(),'\n')

        data_dict = json.loads(data)
        if isinstance(data_dict, dict):
            if 'message' in data_dict['data']:
                print(' data has msg ')
                if 'result' in data_dict['data']['message']:
                    print('message has result')
                    if data_dict['data']['message']['result']=='success':
                        print(' handshake sucessfull!')
                        print('set given id from driver')
                        self.id = data_dict['sessionID']
                        self.topic['self'] = 'com.opentrons.'+self.id
                        self.driverID = data_dict['from']
                        print('try to shake hands??')
##                        try:                            
##                        self.session_factory.session.subscribe(self.dispatch_message,self.topic['self'])
                        self.publish('com.opentrons.driver_handshake','driver',self.id,'handshake','TCP comm','shake','true')
##                        input('wait for a second')
##                        self.publish('driver',self.driverID,self.id,'command','smoothie','home',{'X':''})
##                        except:
##                            print('handshake shake rejected')
                    else:
                        print('handshake failed')
                else:
                    print('no handshake result')
            else:
                print('no message in data')
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
##            if 'from' in data:
##                print('* data has "from"')
##                client_id = data_dict['from']
##                print('client_id: ',client_id)
##                if client_id in self.clients:
##                    print('* from is a client')
##                    if 'data' in data_dict:
##                        if 'message' in data_dict['data']:
##                            if 'extend' in data_dict['data']['message']:
##                                print('handshake called again on client ',client_id,'. We could have done something here to repopulate data')
##                                self.publish( client_id , client_id , client_id, 'handshake','driver','result','already_connected')
##                            if 'shake' in data_dict['data']['message']:
##                                self.publish_client_ids(client_id,client_id)
##                else:
##                    print('* from is NOT a client')
##                    if len(self.clients) > self.max_clients:
##                        self.publish( 'frontend', '' , '' , 'handshake' , 'driver' , 'result' , 'fail' )
##                    else:
##                        if client_id != "":
##                            self.clients[client_id] = 'com.opentrons.'+client_id
##                            self.publish( 'frontend' , client_id , client_id, 'handshake', 'driver', 'result','success')
##                        else:
##                            self.gen_client_id()
##            else:
##                print('* data does NOT have "from"')
##                self.gen_client_id()
##
##            if 'get_ids' in data_dict:
##                publish_client_ids('','')
##        else:
##            self.gen_clien_tid()
##
##
##    def gen_client_id(self):
##        print(datetime.datetime.now(),' - DriverClient.gen_client_id:')
##        #print('\n\targs: ',locals(),'\n')
##        ret_id = ''
##        if len(self.clients) > self.max_clients:
##            self.publish( 'frontend', '' , '' , 'handshake' , 'driver' , 'result' , 'fail' )
##        else:
##            client_id = str(uuid.uuid4())
##            self.clients[client_id] = 'com.opentrons.'+client_id
##            self.publish( 'frontend' , client_id , client_id , 'handshake' , 'driver' , 'result' , 'success' )
##            ret_id = client_id
##        return ret_id


##    def client_check(self, id_, session_id):
##        print(datetime.datetime.now(),' - DriverClient.client_check:')
##        #print('\n\targs: ',locals(),'\n')
##        if id_ in self.clients:
##            return True
##        else:
##            return False
##
##
##    def publish_client_ids(self, id_, session_id):
##        print(datetime.datetime.now(),' - DriverClient.publish_client_ids:')
##        #print('\n\targs: ',locals(),'\n')
##        if id_ in self.clients:
##            self.publish( id_ , id_ , session_id, 'handshake' , 'driver' , 'ids' , list(self.clients) )
##        else:
##            self.publish( 'frontend' , '' , session_id, 'handshake' , 'driver' , 'ids' , list(self.clients) )
##        return list(self.clients)
##
##
    def publish(self,topic,to,session_id,type_,name,message,param):
        """
        """
        print(datetime.datetime.now(),' - DriverClient.publish:')
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
                        elif topic in self.clients:
                            print('TO: ',to)
                            url_topic = 'com.opentrons.'+to
                            print(datetime.datetime.now(),'url topic: ',url_topic)
                            self.session_factory._myAppSession.publish(self.clients.get(topic),json.dumps(msg))
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


    # FUNCTIONS FROM HARNESS
##    def drivers(self, from_, session_id, name, param):
##        """
##        name: n/a
##        param: n/a
##        """
##        print(datetime.datetime.now(),'- DriverClient.drivers:')
##        #print('\n\targs: ',locals(),'\n')
##        return_list = list(self.driver_dict)
##        if name is None:
##            name = 'None'
##        if from_ == "":
##            self.publish('frontend',from_,session_id,'driver',name,'drivers',return_list)
##        else:
##            self.publish(from_,from_,session_id,'driver',name,'drivers',return_list)
##        return return_list
##
##
##    def add_driver(self, from_, session_id, name, param):
##        """
##        name: name of driver to add_driver
##        param: driver object
##        """
##        print(datetime.datetime.now(),' - DriverClient.add_driver:')
##        #print('\n\targs: ',locals(),'\n')
##        self.driver_dict[name] = param
##        return_list = list(self.driver_dict)
##        if from_ == "":
##            self.publish('frontend',from_,session_id,'driver',name,'drivers',return_list)
##        else:
##            self.publish(from_,from_,session_id,'driver',name,'drivers',return_list)
##        return return_list
##
##
##    def remove_driver(self, from_, session_id, name, param):
##        """
##        name: name of driver to be driver
##        param: n/a
##        """
##        print(datetime.datetime.now(),' - DriverClient.remove_driver:')
##        #print('\n\targs: ',locals(),'\n')
##        del self.driver_dict[name]
##        return_list = list(self.driver_dict)
##        if from_ == "":
##            self.publish('frontend',from_,session_id,'driver',name,'drivers',return_list)
##        else:
##            self.publish(from_,from_,session_id,'driver',name,'drivers',return_list)


##    def callbacks(self, from_, session_id, name, param):
##        """
##        name: name of driver
##        param: n/a
##        """
##        print(datetime.datetime.now(),' - DriverClient.callbacks:')
##        #print('\n\targs: ',locals(),'\n')
##        return_dict = self.driver_dict[name].callbacks()
##        if from_ == "":
##            self.publish('frontend',from_,session_id,'driver',name,'callbacks',return_dict)
##        else:
##            self.publish(from_,from_,session_id,'driver',name,'callbacks',return_dict)
##        return return_dict
##
##
##    def meta_callbacks(self, from_, session_id, name, param):
##        """
##        name: name of driver
##        param: n/a
##        """
##        print(datetime.datetime.now(),' - DriverClient.meta_callbacks:')
##        #print('\n\targs: ',locals(),'\n')
##        return_dict = self.driver_dict[name].meta_callbacks()
##        self.publish(from_,from_,session_id,'driver',name,'meta_callbacks',return_dict)
##        return return_dict
##
##
##    def set_meta_callback(self, from_, session_id, name, param):
##        """
##        name: name of driver
##        param: { meta-callback-name : meta-callback-object }
##        """
##        print(datetime.datetime.now(),' - DriverClient.set_meta_callback:')
##        #print('\n\targs: ',locals(),'\n')
##        if isinstance(param,dict):
##            return_dict = self.driver_dict.get(name).set_meta_callback(list(param)[0],list(param.values())[0])
##        else:
##            return_dict = self.driver_dict.get(name).meta_callbacks()
##        self.publish(from_,from_,session_id,'driver',name,'meta_callback',return_dict)
##        return return_dict
##
##
##    def add_callback(self, from_, session_id, name, param):
##        """
##        name: name of driver
##        param: { callback obj: [messages list] }
##        """
##        print(datetime.datetime.now(),' - DriverClient.add_callback:')
##        #print('\n\targs: ',locals(),'\n')
##        return_dict = self.driver_dict.get(name).add_callback(list(param)[0],list(param.values())[0])
##        if from_ == "":
##            self.publish('frontend',from_,session_id,'driver',name,'callbacks',return_dict)
##        else:
##            self.publish(from_,from_,session_id,'driver',name,'callbacks',return_dict)
##
##
##    def remove_callback(self, from_, session_id, name, param):
##        """
##        name: name of driver
##        param: name of callback to remove
##        """
##        print(datetime.datetime.now(),' - DriverClient.remove_callback:')
##        #print('\n\targs: ',locals(),'\n')
##        return_dict = self.driver_dict[name].remove_callback(param)
##        if from_ == "":
##            self.publish('frontend',from_,session_id,'driver',name,'callbacks',return_dict)
##        else:
##            self.publish(from_,from_,session_id,'driver',name,'callbacks',return_dict)
##        return return_dict
##
##
##    def flow(self, from_, session_id, name, param):
##        """
##        name: name of driver
##        param: n/a
##        """
##        print(datetime.datetime.now(),' - DriverClient.flow:')
##        #print('\n\targs: ',locals(),'\n')
##        return_dict = self.driver_dict.get(name).flow()
##        if from_ == "":
##            self.publish('frontend',from_,session_id,'driver',name,'flow',return_dict)
##        else:
##            self.publish(from_,from_,session_id,'driver',name,'flow',return_dict)
##        return return_dict
##
##
##    def clear_queue(self, from_, session_id, name, param):
##        """
##        name: name of driver
##        param: n/a
##        """
##        print(datetime.datetime.now(),' - DriverClient.clear_queue:')
##        #print('\n\targs: ',locals(),'\n')
##        return_dict = self.driver_dict.get(name).clear_queue()
##        if from_ == "":
##            self.publish('frontend',from_,session_id,'labware',name,'clear_queue',return_dict)
##        else:
##            self.publish(from_,from_,session_id,'labware',name,'clear_queue',return_dict)
##        return return_dict
##
##
##    def driver_connect(self, from_, session_id, name, param):
##        """
##        name: name of driver
##        param: n/a
##        """
##        print(datetime.datetime.now(),' - DriverClient.driver_connect:')
##        #print('\n\targs: ',locals(),'\n')
##        print('self.driver_dict: ',self.driver_dict)
##        print('self.driver_dict[',name,']: ',self.driver_dict[name])
##        self.driver_dict[name].connect(from_,session_id)    # <--- This should lead to on_connection_made callback
##
##
##    def driver_disconnect(self, from_, name, param):
##        """
##        name: name of driver
##        param: n/a
##        """
##        print(datetime.datetime.now(),' - DriverClient.driver_disconnect:')
##        #print('\n\targs: ',locals(),'\n')
##        self.driver_dict.get(name).disconnect(from_,session_id) # <--- This should lead to on_connection_lost callback
##
##
##    def commands(self, from_, session_id, name, param):
##        """
##        name: name of driver
##        param: n/a
##        """
##        print(datetime.datetime.now(),' - DriverClient.commands:')
##        #print('\n\targs: ',locals(),'\n')
##        return_dict = self.driver_dict.get(name).commands()
##        self.publish(from_,from_,session_id,'driver',name,'commands',return_dict)
##        return return_dict
##
##
##    def meta_commands(self, from_, session_id, name, param):
##        """
##        name: name of driver
##        param: n/a
##        """
##        print(datetime.datetime.now(),' - DriverClient.meta_commands:')
##        #print('\n\targs: ',locals(),'\n')
##        return_list = list(self.meta_dict)
##        if from_ == "":
##            self.publish('frontend',from_,session_id,'driver',name,'meta_commands',return_list)
##        else:
##            self.publish(from_,from_,session_id,'driver',name,'meta_commands',return_list)
##        return return_list
##
##
##    def configs(self, from_, session_id, name, param):
##        """
##        name: name of driver
##        param: n/a
##        """
##        print(datetime.datetime.now(),' - DriverClient.configs:')
##        #print('\n\targs: ',locals(),'\n')
##        return_dict = self.driver_dict.get(name).configs()
##        if from_ == "":
##            self.publish('frontend',from_,session_id,'driver',name,'configs',return_dict)
##        else:
##            self.publish(from_,from_,session_id,'driver',name,'configs',return_dict)
##        return return_dict
##
##
##    def set_config(self, from_, session_id, name, param):
##        """
##        name: name
##        param: { config name : config value }
##        """
##        print(datetime.datetime.now(),' - DriverClient.set_config:')
##        #print('\n\targs: ',locals(),'\n')
##        if isinstance(param,dict):
##            self.driver_dict.get(name).set_config(list(param)[0],list(param.values)[0])
##        return_dict = self.driver_dict.get(name).configs()
##        if from_ == "":
##            self.publish('frontend',from_,session_id,'driver',name,'configs',return_dict)
##        else:
##            self.publish(from_,from_,session_id,'driver',name,'configs',return_dict)
##        return return_dict
##
##
##    def meta_command(self, from_, session_id, data):
##        """
##
##        data should be in the form:
##
##        {
##            'name': name,
##            'message': value
##        }
##
##        where name the name of the driver or None if n/a,
##
##        and value is one of two forms:
##
##        1. string
##
##        2. {command:params}
##            params --> {param1:value, ... , paramN:value}
##
##
##        """
##        print(datetime.datetime.now(),' - DriverClient.meta_command:')
##        #print('\n\targs: ',locals(),'\n')
##        if isinstance(data, dict):
##            name = data['name']
##            value = data['message']
##            if name in self.driver_dict:
##                if isinstance(value, dict):
##                    command = list(value)[0]
##                    params = value[command]
##                    try:
##                        self.meta_dict[command](from_,session_id,name,params)
##                    except:
##                        if from_ == "":
##                            self.publish('frontend',from_,session_id,'driver',name,'error',sys.exc_info())
##                        else:
##                            self.publish(from_,from_,session_id,'driver',name,'error',sys.exc_info())
##                        print(datetime.datetime.now(),' - meta_command error: ',sys.exc_info())
##                elif isinstance(value, str):
##                    command = value
##                    try:
##                        self.meta_dict[command](from_,session_id,name,None)
##                    except:
##                        if from_ == "":
##                            self.publish('frontend',from_,session_id,'driver',name,'error',sys.exc_info())
##                        else:
##                            self.publish(from_,from_,session_id,'driver',name,'error',sys.exc_info())
##                        print(datetime.datetime.now(),' - meta_command error: ',sys.exc_info())
##            else:
##                if isinstance(value, dict):
##                    command = list(value)[0]
##                    params = value[command]
##                    try:
##                        self.meta_dict[command](from_,session_id,None, params)
##                    except:
##                        if from_ == "":
##                            self.publish('frontend',from_,session_id,'driver',name,'error',sys.exc_info())
##                        else:
##                            self.publish(from_,from_,session_id,'driver',name,'error',sys.exc_info())
##                        print(datetime.datetime.now(),' - meta_command error, name not in drivers: ',sys.exc_info())
##                elif isinstance(value, str):
##                    command = value
##                    try:
##                        self.meta_dict[command](from_,session_id,None,None)
##                    except:
##                        if from_ == "":
##                            self.publish('frontend',from_,session_id,'driver','None','error',sys.exc_info())
##                        else:
##                            self.publish(from_,from_,session_id,'driver','None','error',sys.exc_info())
##                        print(datetime.datetime.now(),' - meta_command error, name not in drivers: ',sys.exc_info())
##
##
##    def send_command(self, from_, session_id, data):
##        """
##        data:
##        {
##            'name': name of driver
##            'message': string or { message : {param:values} } <--- the part the driver cares about
##        }
##        """
##        print(datetime.datetime.now(),' - DriverClient.send_command:')
##        #print('\n\targs: ',locals(),'\n')
##        if isinstance(data, dict):
##            name = data['name']
##            value = data['message']
##            if name in self.driver_dict:
##                try:
##                    self.driver_dict[name].send_command(from_, session_id, value)
##                except:
##                    if from_ == "":
##                        self.publish('frontend',from_,session_id,'driver',name,'error',sys.exc_info())
##                    else:
##                        self.publish(from_,from_,session_id,'driver',name,'error',sys.exc_info())
##                    print(datetime.datetime.now(),' - send_command error: '+sys.exc_info())
##            else:
##                if from_ == "":
##                    self.publish('frontend',from_,session_id,'driver','None','error',sys.exc_info())
##                else:
##                    self.publish(from_,from_,session_id,'driver','None','error',sys.exc_info())
##                print(datetime.datetime.now(),' - send_command_error, name not in drivers: '+sys.exc_info())
##
##
    def _make_connection(self, url_protocol='ws', url_domain='0.0.0.0', url_port=8080, url_path='ws', debug=False, debug_wamp=False):
        print(datetime.datetime.now(),' - DriverClient._make_connection:')
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
        print(datetime.datetime.now(),' - DriverClient.connect:')
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
        print(datetime.datetime.now(),' - DriverClient.disconnect:')
        #print('\n\targs: ',locals(),'\n')
        self.transport.close()
        self.transport_factory = None


#This was mostly based off of the github gregvish/chat.py code




class Peer(object):
    def __init__(self, server, sock, name):
        self.loop = server.loop
        self.name = name
        self._sock = sock
        self._server = server
        self.id = self._server._translator.id
##        self.translator = TCPtranslator(self._server.loop)
        # point to relay server for TCP translator
##        self.translator.relay = self._server
##
##        self.translator.connect(
##            url_domain= '0.0.0.0',
##            url_port=8080
##            )
        if self.name[0] == '127.0.0.1':
            self.global_name = 'com.opentrons.robot_to_tcp'
        else:
            self.global_name = 'com.opentrons.tcp_to_robot'
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
            if buf == b'':
                break
##            self._server.broadcast('%s: %s' % (self.name, buf.decode('utf8')))
            #print("new msg")
##            rawMsg = buf;
##            msgIn = buf.decode('utf8')
##            print(buf)
            buffOut = buf.decode('utf8')
            cleanMsg = buffOut.strip('\n\r')
##            print(buf)
            print(cleanMsg)
##            self._server.relay(cleanMsg,self.global_name)
            rawtojson = json.loads(cleanMsg)
##            opic,to,session_id,type_,name,message,param):
            
            self._server._translator.publish(rawtojson['topic'],self._server._translator.driverID,
                                             self._server._translator.id,rawtojson['type'],
                                             rawtojson['name'],rawtojson['message'],rawtojson['param'])
##            self._server._translator.publish('driver',self._server._translator.driverID,self._server._translator.id,'command','smoothie','home',{'X':''})
##            self._server.broadcast('%s\t%s' % (self.global_name, cleanMsg))
##            self._server.relay('%s\t%s' % (self.global_name, buf.decode('utf8')),self._sock)       
class rawTcpServer(object):
    def __init__(self, loop, port, translator):
        self.loop = loop
        self._serv_sock = socket()
        self._serv_sock.setblocking(0)
        self._serv_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self._serv_sock.bind(('',port))
        self._serv_sock.listen(0)
        self._peers = []
        self._translator = translator
        Task(self._server())

    def remove(self, peer):
        self._peers.remove(peer)
        self.broadcast('%s\tquit!\n\r' % (peer.global_name,))

    def broadcast(self, message):
##        print(list(self._peers))
        print("TCP Server: sending msg")
        print(message)
        for peer in self._peers:
            peer.send(message)

##    def sendTo(self,
    def relay(self, message, incomingSock):
##        print(list(set(incomingSock)-set(self._peers)))
        
        for peer in self._peers:
            if peer._sock != incomingSock:
                peer.send(message)

    def passMsg(self, msg, peer_id):
        msgOut = msg + '\n\r'
        for peer in self._peers:
            if peer.id == peer_id:
                peer.send(msgOut)

                
    @coroutine
    def _server(self):
        while True:
            peer_sock, peer_name = yield from self.loop.sock_accept(self._serv_sock)
            peer_sock.setblocking(0)
##            print(datetime.datetime.now(),' - INITIAL SETUP - publisher, harness, subscriber ','* * '*10)
            peer = Peer(self, peer_sock, peer_name)
            self._peers.append(peer)

            # TRYING THE FOLLOWING IN INSTANTIATE OBJECTS vs here
            # INITIAL SETUP
            
##            TCP_trans = TCPtranslator()

##            # point to relay server for TCP translator
##            TCP_trans.relay = relayServer
            time_string = str(datetime.datetime.now())
            msg = {'time':time_string, 'type':'TCP handshake','to':self._translator.id,'from':'com.opentrons.tcpRelay','sessionID':self._translator.id}
            delimMsg = json.dumps(msg) + '\n\r'
            print(delimMsg.encode())
            peer.send(delimMsg)
##            self.broadcast('%s\tconnected!\n\r' % (peer.global_name,))
##            print(peer_name[0]=='127.0.0.1')
            #print(peer_sock)

### 

##def main():
##    loop = get_event_loop()
##    relayServer = rawTcpServer(loop, 7887)
##    loop.call_later(10,relayServer.broadcast,'test msg \n\r')


if __name__ == '__main__':

    try:

        
##        loop.call_later(10,relayServer.broadcast,'test msg \n\r')
##        loop.run_forever()
        #session_factory = wamp.ApplicationSessionFactory()
        #session_factory.session = WampComponent
        #session_factory._myAppSession = None

        #url = "ws://0.0.0.0:8080/ws"
        #transport_factory = websocket.WampWebSocketClientFactory(session_factory,
        #                                                        url=url,
        #                                                        debug=False,
        #                                                        debug_wamp=False)
        #loop = asyncio.get_event_loop()

        print('\nBEGIN INIT...\n')
        loop = get_event_loop()
        # TRYING THE FOLLOWING IN INSTANTIATE OBJECTS vs here
        # INITIAL SETUP
        print(datetime.datetime.now(),' - INITIAL SETUP - publisher, harness, subscriber ','* * '*10)
        TCP_trans = TCPtranslator(loop)

        # START RAW TCP SERVER
        serverPort = 7887
        relayServer = rawTcpServer(loop, serverPort, TCP_trans)

        # point to relay server for TCP translator
        TCP_trans.relay = relayServer

        # INSTANTIATE DRIVERS
##        print(datetime.datetime.now(),' - INSTANTIATE DRIVERS - smoothie_driver ','* * '*10)
##        smoothie_driver = SmoothieDriver(simulate=(os.environ.get('SMOOTHIE_SIMULATE', 'true')=='true'))


        # ADD DRIVERS
##        print(datetime.datetime.now(),' - ADD DRIVERS ','* * '*10)   
##        driver_client.add_driver(driver_client.id,'','smoothie',smoothie_driver)
##        print(driver_client.drivers(driver_client.id,'',None,None))


        # DEFINE CALLBACKS
        #
        #   data_dict format:
        #
        #
        #
        #
        #
##        print(datetime.datetime.now(),' - DEFINE CALLBACKS ','* * '*10)
##        def none(name, from_, session_id, data_dict):
##            """
##            """
##            print(datetime.datetime.now(),' - driver_client.none:')
##            print('\n\targs: ',locals(),'\n')
##            dd_name = list(data_dict)[0]
##            dd_value = data_dict[dd_name]
##            driver_client.publish('frontend',from_,session_id,'driver',name,list(data_dict)[0],dd_value)
##            if from_ != session_id:
##                driver_client.publish(from_,from_,session_id,'driver',name,list(data_dict)[0],dd_value)
##
##        def positions(name, from_, session_id, data_dict):
##            """
##            """
##            print(datetime.datetime.now(),' - driver_client.positions:')
##            print('\n\targs: ',locals(),'\n')
##            dd_name = list(data_dict)[0]
##            dd_value = data_dict[dd_name]
##            driver_client.publish('frontend',from_,session_id,'driver',name,list(data_dict)[0],dd_value)
##            if from_ != session_id:
##                driver_client.publish(from_,from_,session_id,'driver',name,list(data_dict)[0],dd_value)
##
##        def adjusted_pos(name, from_, session_id, data_dict):
##            """
##            """
##            print(datetime.datetime.now(),' - driver_client.adjusted_pos:')
##            print('\n\targs: ',locals(),'\n')
##            dd_name = list(data_dict)[0]
##            dd_value = data_dict[dd_name]
##            driver_client.publish('frontend',from_,session_id,'driver',name,list(data_dict)[0],dd_value)
##            if from_ != session_id:
##                driver_client.publish(from_,from_,session_id,'driver',name,list(data_dict)[0],dd_value)
##
##        def smoothie_pos(name, from_, session_id, data_dict):
##            """
##            """
##            print(datetime.datetime.now(),' - driver_client.smoothie_pos:')
##            print('\n\targs: ',locals(),'\n')
##            dd_name = list(data_dict)[0]
##            dd_value = data_dict[dd_name]
##            driver_client.publish('frontend',from_,session_id,'driver',name,list(data_dict)[0],dd_value)
##            if from_ != session_id:
##                driver_client.publish(from_,from_,session_id,'driver',name,list(data_dict)[0],dd_value)
##
##
##
##
##        # ADD CALLBACKS
##        print('*\t*\t* add callbacks via harness\t*\t*\t*')
##        driver_client.add_callback(driver_client.id,'','smoothie', {none:['None']})
##        driver_client.add_callback(driver_client.id,'','smoothie', {positions:['M114']})
##        driver_client.add_callback(driver_client.id,'','smoothie', {adjusted_pos:['adjusted_pos']})
##        driver_client.add_callback(driver_client.id,'','smoothie', {smoothie_pos:['smoothie_pos']})
##
##        for d in driver_client.drivers(driver_client.id,'',None,None):
##            print (driver_client.callbacks(driver_client.id,'',d, None))
##
##
##        # ADD METACALLBACKS
##        print(datetime.datetime.now(),' - DEFINE AND ADD META-CALLBACKS ','* * '*10)
##        def on_connect(from_,session_id):
##            print(datetime.datetime.now(),' - driver_client.on_connect')
##            print('\n\targs: ',locals(),'\n')
##            driver_client.publish(from_,from_,session_id,'connect','driver','result','connected')
##
##        def on_disconnect(from_,session_id):
##            print(datetime.datetime.now(),' - driver_client.on_disconnect')
##            print('\n\targs: ',locals(),'\n')
##            driver_client.publish(from_,from_,session_id,'connect','driver','result','disconnected')
##
##        def on_empty_queue(from_,session_id):
##            print(datetime.datetime.now(),' - driver_client.on_empty_queue')
##            print('\n\targs: ',locals(),'\n')
##            driver_client.publish(from_,from_,session_id,'queue','driver','result','empty')
##
##        def on_raw_data(from_,session_id,data):
##            print(datetime.datetime.now(),' - driver_client.on_raw_data')
##            print('\n\targs: ',locals(),'\n')
##            driver_client.publish(from_,from_,session_id,'raw','driver','data',data)
##
##
##        driver_client.set_meta_callback(driver_client.id,'','smoothie',{'on_connect':on_connect})
##        driver_client.set_meta_callback(driver_client.id,'','smoothie',{'on_disconnect':on_disconnect})
##        driver_client.set_meta_callback(driver_client.id,'','smoothie',{'on_empty_queue':on_empty_queue})
##        driver_client.set_meta_callback(driver_client.id,'','smoothie',{'on_raw_data':on_raw_data})
##
##        # CONNECT TO DRIVERS:
##        print(datetime.datetime.now(),' - CONNECT TO DRIVERS ','* * '*10)
##        driver_client.driver_connect(driver_client.id,'','smoothie',None)

        print('END INIT')

##        TCP_trans.connect(
##            url_domain=os.environ.get('CROSSBAR_HOST', '0.0.0.0'),
##            url_port=int(os.environ.get('CROSSBAR_PORT', '8080'))
##            )
        TCP_trans.connect(
            url_domain= '0.0.0.0',
            url_port=8080
            )

    except KeyboardInterrupt:
        pass
    finally:
        print('disconnect')
##        for peer in relayServer._peers:
##            peer.translator.disconnect()
        TCP_trans.disconnect()
        print('ALL DONE!')














