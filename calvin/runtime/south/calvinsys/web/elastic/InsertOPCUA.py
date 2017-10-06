# -*- coding: utf-8 -*-

# Copyright (c) 2017 Ericsson AB
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

import requests
import re

from calvin.runtime.south.plugins.async import threads
from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.south.calvinsys import base_calvinsys_object

_log = get_logger(__name__)

class InsertOPCUA(base_calvinsys_object.BaseCalvinsysObject):
    """
    Insert OPCUA data into Elastic Search
    """

    init_schema = {
        "type": "object",
        "properties": {
            "url": {
                "description": "URL of Elastic Search thingie ",
                "type": "string"
            },
            "tag": {
                "description": "Tag to use in index",
                "type": "string"
            },
            "username": {
                "description": "Username",
                "type" : ["string", "null"]
            },
            "password": {
                "description": "Password",
                "type": ["string", "null"]
            }
        },
        "description": "Setup Elastic Search endpoint to receive OPCUA"
    }
    
    can_write_schema = {
        "description": "True if ready for more data",
        "type": "boolean"
    }

    write_schema = {
        "description": "Send data to Elastic Search",
        "type": "object"
    }

    can_read_schema = {
        "description": "Returns True iff request has finished",
        "type": "boolean"
    }
    
    read_schema = {
        "description": "Get result from request, a status code",
        "type" : "integer"
    }

    doctypes_d = {
        "opcua": {
            "origin": {"type": "string"},
            "calvints": {"type": "date", "format": "epoch_millis"},
            "sourcets": {"type": "date", "format": "yyyy-MM-dd HH:mm:ss.SSSSSS"},
            "tag": {"type": "string"},
            "value": {"type": "float"},
            "id": {"type": "string"},
            "info": {"type": "string"},
            "status": {"type": "string"},
            "serverts": {"type": "date", "format": "yyyy-MM-dd HH:mm:ss.SSSSSS"},
            "type": {"type": "string"}
        }
    }

    re_date_full = re.compile('[0-9]{4}-[0-9]{2}-[0-9]{2}\s+[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]+')
    re_date_no_ms = re.compile('[0-9]{4}-[0-9]{2}-[0-9]{2}\s+[0-9]{2}:[0-9]{2}:[0-9]{2}$')

    def init(self, url, tag, username, password):
        self._url = url
        self._tag = tag
        self._doctype = "opcua"
        self._username = username
        self._password = password
        
        self._running = None
        self._status = None
        
        self.known_mappings = []

        self.mapping = {"mappings": {}}
        for d in InsertOPCUA.doctypes_d:
            prop = InsertOPCUA.doctypes_d[d]
            self.mapping["mappings"][d] = {"properties": prop}

    def can_write(self):
        return self._running is None
        

    def _wash(self, js):
        if js.get("type") in ["Float", "Double"]:
            js["value"] = float(js.get("value", 0))
            js["type"] = "Float"
        else :
            return None

        for entry in ["calvints", "origin", "tag", "value", "info", "status", "type"]:
            if not entry in js :
                print("Required entry {} missing".format(entry))
                return None

        def _checkts(ts):
            if not InsertOPCUA.re_date_full.search(js[ts]):
                if InsertOPCUA.re_date_no_ms.search(js[ts]):
                    js[ts] += ".000000" # add ms
                else :
                    js[ts] = ""

        for ts in ['sourcets', 'serverts']:
            if js.setdefault(ts, ""):
                _checkts(ts)

        js['sourcets'] = js['sourcets'] or js['serverts']
        js['serverts'] = js['serverts'] or js['sourcets']

        return js if js.get('sourcets') else None
    
    def _exec(self, cmdlist):
        for cmd in cmdlist: # A list to handle new indices
            func, url, data = cmd["func"], cmd["url"], cmd["data"]
            res = func(url=url, json=data, auth=(self._username, self._password))
        return res.status_code

    def _result(self, status):
        self._status = status
        self.scheduler_wakeup()

    def write(self, data):
        # wash the data
        js = self._wash(data)

        if not js:
            self._status = 500 # Generic error
            
        def _make_index():
            return "log--%s-%s" % (self._tag, js["serverts"].split(" ")[0])

        cmdlist = []

        index = _make_index()
        # in case of a new index, we need to set the mapping 
        if index not in self.known_mappings:
            self.known_mappings.append(index)
            url = "%s/%s?pretty" % (self._url, index)
            cmdlist.append({"func": requests.put, "url": url, "data": self.mapping})

        url = "%s/%s/%s" % (self._url, index, self._doctype)
        cmdlist.append({"func": requests.post, "url": url, "data": js})

        self._running = threads.defer_to_thread(self._exec, cmdlist)
        self._running.addBoth(self._result)


    def can_read(self):
        return self._running is not None and self._status is not None

    def read(self):
        self._running = None
        status = self._status
        self._status = None
        return status
        
    def close(self):
        if self._running:
            self._running.cancel()
        pass
