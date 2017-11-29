
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

from calvin.runtime.south.calvinsys import base_calvinsys_object

class BaseQueue(base_calvinsys_object.BaseCalvinsysObject):
    """
    Queue - API for basic data structure
    """

    init_schema = {
        "type": "object",
        "properties": {
            "queue_id": {
                "description": "Queue identifier"
            }
        },
        "description": "Initialize queue"
    }
    
    can_write_schema = {
        "description": "Returns True if queue ready for push, otherwise False",
        "type": "boolean"
    }

    write_schema = {
        "description": "Push data to queue"
    }

    can_read_schema = {
        "description": "Returns True if queue can be popped, otherwise False",
        "type": "boolean"
    }

    read_schema = {
        "description": "Pop data from queue"
    }

    def init(self, **kwargs):
        raise NotImplementedError()

    def can_write(self):
        raise NotImplementedError()

    def write(self, value):
        raise NotImplementedError()

    def can_read(self):
        raise NotImplementedError()

    def read(self):
        raise NotImplementedError()

    def close(self):
        raise NotImplementedError()