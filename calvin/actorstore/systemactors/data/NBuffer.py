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


class NBuffer(Actor):
    """
    Buffer data to file (when necessary.)
    Inputs:
      list : a _list_ of data to be buffered

    Outputs:
        list : an identical list, eventually
    """
    
    def exception_handler(self, action, args):
        # Drop any incoming exceptions
        return action(self, None)
        
    @manage(["buffer_name", "received", "sent", "interval"])
    def init(self, buffer_name, interval):
        self.buffer_name = buffer_name
        self.interval = interval
        self.received = 0
        self.sent = 0
        self.timer = calvinsys.open(self, "sys.timer.once")
        calvinsys.write(self.timer, 10) # Wait a while
        self.fifo = calvinsys.open(self, 'data.queue', queue_id=self.buffer_name) 



    @stateguard(lambda self: calvinsys.can_read(self.timer))
    @condition([], [])
    def logger(self):
        calvinsys.read(self.timer)
        _log.info("{}: received: {}, sent: {}".format(self.buffer_name, self.received, self.sent))
        calvinsys.write(self.timer, self.interval)

    @stateguard(lambda self:calvinsys.can_write(self.fifo))
    @condition(['list'], [])
    def push_data(self, data):
        self.received += len(data)
        calvinsys.write(self.fifo, data)

    @stateguard(lambda self: calvinsys.can_read(self.fifo))
    @condition([], ['list'])
    def pop_data(self):
        data = calvinsys.read(self.fifo)
        self.sent += len(data)
        return (data, )

    action_priority = (logger, pop_data, push_data)
    
    requires = ['data.queue', 'json', 'sys.timer.once']
