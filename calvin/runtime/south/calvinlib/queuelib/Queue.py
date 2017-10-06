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

from calvin.runtime.south.calvinlib import base_calvinlib_object
import collections

class Queue(base_calvinlib_object.BaseCalvinlibObject):
    """
    Basic queue implementation
    """

    init_schema = {
        "description": "setup queue lib",
    }
    
    new_schema = {
        "description": "create queue",
        "type": "integer"
    }

    def init(self):
        pass
        
    def new(self, maxlen=None):
        return collections.deque(maxlen=maxlen)

