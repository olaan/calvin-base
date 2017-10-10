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

from calvin.runtime.south.calvinsys import base_calvinsys_object
from calvin.utilities.calvinlogger import get_logger
from PortCollection import port_collection

_log = get_logger(__name__)


class OutPort(base_calvinsys_object.BaseCalvinsysObject):
    """
    Naive first shot at application comm
    """

    init_schema = {
        "type": "object",
        "properties": {
            "tag": {
                "description": "Identifier of this outport",
                "type": "string"
            },
            "length": {
                "description": "Maximum length of the queue",
                "type": "integer",
                "maximum": 1025,
                "minimum": 1
            }
            
        },
        "description": "Incoming data is made available to other application"
    }

    can_write_schema = {
        "description": "Always true",
        "type": "boolean"
    }

    write_schema = {
        "description": "Write data to port",
        "type": ["boolean", "integer", "number", "string", "array", "object"]
    }

    def init(self, tag, length=100, **kwargs):
        self._tag = tag
        self._length = length
        self._queue = None

    def can_write(self):
        if self._queue is None:
            # attempt to create port if not exist
            # handles deserialization as well as duplicate tags
            self._queue = port_collection().new_port(self._tag, self._length)
        return port_collection().port_claimed(self._tag)

    def write(self, data):
        self._queue.appendleft(data)

    def close(self):
        port_collection().remove_port(self.tag)
        
