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


from collections import deque
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class PortCollection(object):
    _ports = {}

    def claim_port(self, tag):
        port = PortCollection._ports.get(tag)
        if port and port["available"]:
            port["available"] = False
            return port["queue"]
        return None

    def release_port(self, tag):
        port = PortCollection._ports.get(tag)
        if port:
            port["available"] = True
        
    def new_port(self, tag, length):
        if PortCollection._ports.get(tag):
            return None
        else:
            PortCollection._ports[tag] = { "available": True, "queue": deque(maxlen=length)}
            return PortCollection._ports[tag]["queue"]
            
    def remove_port(self, tag):
        if PortCollection._ports.get(tag):
            PortCollection._ports.pop(tag)
            
    def port_claimed(self, tag):
        if tag in PortCollection._ports:
            return not PortCollection._ports[tag]["available"]
        return False

_port_collection = None

def port_collection():
    global _port_collection
    if not _port_collection:
        _port_collection = PortCollection()
    return _port_collection