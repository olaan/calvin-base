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


class AppSink(Actor):
    """
    Allow data to be sent to other application - on same runtime!

    Inputs:
      data : some data, any data

    """
    
    @manage(['outport'])
    def init(self, tag):
        self.outport = calvinsys.open(self, "app.outport", tag=tag)

    def will_end(self):
        calvinsys.close(self.outport)

    @stateguard(lambda self: calvinsys.can_write(self.outport))
    @condition(['data'], [])
    def receive(self, data):
        calvinsys.write(self.outport, data)

    action_priority = (receive, )
    
    requires = ['app.outport']