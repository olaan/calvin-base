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

from PortCollection import port_collection

from calvin.runtime.south.calvinsys import base_calvinsys_object
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class InPort(base_calvinsys_object.BaseCalvinsysObject):
    """
    Naive first shot at application comm
    """

    init_schema = {
        "type": "object",
        "properties": {
            "tag": {
                "description": "Tag of port to read from",
                "type": "string"
            }
        },
        "required": ["tag"],
        "description": "Read data from other application via application port"
    }

    can_read_schema = {
        "description": "True if data available",
        "type": "boolean"
    }

    read_schema = {
        "description": "Read data from port",
        "type": ["boolean", "integer", "number", "string", "array", "object"]
    }

    def init(self, tag, **kwargs):
        self._tag = tag
        self._queue = None

    def can_read(self):
        if self._queue is None:
            # Attempt to claim port, handles migration & duplicate tags
            self._queue = port_collection().claim_port(self._tag)
        return bool(self._queue) # False if empty or None, True otherwise

    def read(self):
        return self._queue.pop()

    def close(self):
        port_collection().release_port(self.tag)

