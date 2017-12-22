# -*- coding: utf-8 -*-

# Copyright (c) 2015 Ericsson AB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.south.plugins.async import async, threads
from calvin.runtime.south.calvinsys import base_calvinsys_object
from urllib2 import Request
from urllib2 import urlopen
from urllib import urlencode
from requests import Session
from signalr import Connection
import json

_log = get_logger(__name__)

class SignalR(base_calvinsys_object.BaseCalvinsysObject):
    """
    Signal R API
    """

    init_schema = {
        "type": "object",
        "properties": {
            "api_key": {
                "description": "API key",
                "type": "string"
            },
            "device_network_id": {
                "description": "Base network id",
                "type": "string"
            },
            "base_url": {
                "description": "Base url",
                "type": "string"
            },
            "resource_ids": {
                "description": "resource(s) to subscribe to (should be list)",
                "type": "array"
            }
        },
        "required": ["api_key", "device_network_id", "base_url", "resource_ids"],
        "description": ""
    }

    can_read_schema = {
        "description": "Returns True if there is data to read, otherwise False",
        "type": "boolean"
    }

    read_schema = {
        "description": "Read data",
        "type": "object"
    }
    
    
    def init(self, api_key, device_network_id, base_url, resource_ids, **kwargs):
        def get_realtime_token_thread():
            headers = {
                "X-DeviceNetwork": self.device_network_id,
                "Authorization": "Bearer " + self.api_key
            }
 
            data = bytes(urlencode({}).encode())
            url = base_url + "/api/v3/deviceNetwork/realtimeToken"
            req = Request(url);
            _log.info("Using {}".format(url))
            req.headers = headers;
            req.data = data;
            res = urlopen(req)
 
            tokendata = res.read().decode('utf-8')
            tokenobject = json.loads(tokendata)
            realtimeToken = tokenobject['Token']
            return realtimeToken
        
        def ready(token):
            self.token = token
            self.subscribe()

        def error(*args, **kwargs):
            _log.info("Failed to get token: {}".format(args))

        self.measurements = []
        self.token = None
        self.api_key = api_key
        self.device_network_id = device_network_id
        self.base_url = base_url
        self.resource_ids = resource_ids
        
        d = threads.defer_to_thread(get_realtime_token_thread)
        d.addCallback(ready)
        d.addErrback(error)


    def subscribe(self):
        def new_measurement(data):
            _log.info("new data: {}".format(data))
            self.measurements.append(data)
            self.scheduler_wakeup()
            
        def new_measurement_thread(data):
            _log.info("new data: {}".format(data))
            async.call_in_thread(new_measurement, data)
        
        def print_error(error):
            _log.info("SignalR error: {}".format(error))
            
        def subscribe_thread():
            def connection_start():
                _log.info("connection started")
                
            def connection_stop():
                _log.info("connection stopped")
                
            
            session = Session()
            connection = Connection(self.base_url + "/signalr", session)
            measurementhub = connection.register_hub('measurementhub')
            connection.start()
            connection.starting += connection_start
            connection.stopping += connection_stop
            connection.error += print_error
            _log.info("connection established.")
            measurementhub.client.on("NewMeasurement", new_measurement_thread)
            measurementhub.server.invoke("authenticate", self.device_network_id, self.token)
            for resource_id in self.resource_ids:
                measurementhub.server.invoke("addSensor", resource_id)
            connection.wait(30)
            return session, connection
                
        def ready(result):
            _log.info("subscription ready {}".format(result))
            self.session, self.connection = result
            
        d = threads.defer_to_thread(subscribe_thread)
        d.addCallback(ready)
        d.addErrback(print_error)

    def can_read(self):
        return bool(self.measurements)
        
    def read(self):
        return self.measurements.pop(0)

    def close(self):
        self.connection.close()
        self.session.close()
