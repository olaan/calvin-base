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


class AppSource(Actor):
    """
    Allow reading data from other application - on same runtime!

    Outputs:
      data : some data, any data

    """
    
    @manage(['inport'])
    def init(self, tag):
        self.inport = calvinsys.open(self, "app.inport", tag=tag)

    def will_end(self):
        calvinsys.close(self.inport)

    @stateguard(lambda self: calvinsys.can_read(self.inport))
    @condition([], ['data'])
    def send(self):
        data = calvinsys.read(self.inport)
        return (data,)

    action_priority = (send, )
    
    requires = ['app.inport']