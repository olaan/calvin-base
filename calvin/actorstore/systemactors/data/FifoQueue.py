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


class FifoQueue(Actor):
    """
    Add incoming data to a queue (fifo)
    Inputs:
      data : data to be queued

    Outputs:
        data : data popped from queue
    """
    
    def exception_handler(self, action, args):
        # Drop any incoming exceptions
        return action(self, None)
        
    @manage([])
    def init(self):
        self.fifo = calvinsys.open(self, "data.queue")

    def will_end(self):
        calvinsys.close(self.fifo)


    @stateguard(lambda self: calvinsys.can_read(self.fifo))
    @condition([], ["data"])
    def pop(self):
        data = calvinsys.read(self.fifo)
        return (data,)
    
    @stateguard(lambda self: calvinsys.can_write(self.fifo))
    @condition(['data'], [])
    def push(self, data):
        calvinsys.write(self.fifo, data)

    action_priority = (pop, push)
    
    requires = ['data.queue']
