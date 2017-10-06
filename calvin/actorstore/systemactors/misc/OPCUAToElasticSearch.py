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

from calvin.actor.actor import Actor, manage, condition, stateguard, calvinsys
from calvin.utilities.calvinlogger import get_actor_logger

_log = get_actor_logger(__name__)


class OPCUAToElasticSearch(Actor):
    """
    Nuthin
    
    Inputs:
      data : Dictionary to send to Elastic Search

    Outputs:
        status : HTTP status code of insert
    """
    
    @manage([])
    def init(self, url, tag, username, password):
        self.handle = calvinsys.open(self, "web.elastic.opcua", url=url, tag=tag, username=username, password=password)
        

    @stateguard(lambda self: calvinsys.can_write(self.handle))
    @condition(['data'], [])
    def receive(self, data):
        calvinsys.write(self.handle, data)

    @stateguard(lambda self: calvinsys.can_read(self.handle))
    @condition([], ['status'])
    def done(self):
        status = calvinsys.read(self.handle)
        return status,

    action_priority = (done, receive)
    
    requires = ['web.elastic.opcua']