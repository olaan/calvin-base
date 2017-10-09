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

from calvin.actor.actor import Actor, manage, condition, stateguard, calvinlib, calvinsys
from calvin.utilities.calvinlogger import get_actor_logger

_log = get_actor_logger(__name__)


class Buffer(Actor):
    """
    Buffer data to file (when necessary.)
    Inputs:
      data : some data

    Outputs:
        data : the same data, eventually
    """
    
    def exception_handler(self, action, args):
        # Drop any incoming exceptions
        return action(self, None)
        
    @manage(["buffer_name", "buffer_limit", "received", "sent", "interval"])
    def init(self, buffer_name, buffer_limit, interval):
        self.buffer_name = buffer_name
        self.buffer_limit = buffer_limit
        self.interval = interval
        self.received = 0
        self.sent = 0
        self.setup()
    
    def setup(self):
        self.json = calvinlib.use("json")
        queuelib = calvinlib.use("queue")
        self.incoming = queuelib.new()
        self.outgoing = queuelib.new()
        # assume something logged to disk (in case of restart)
        self.uses_external = True
        # reset logging
        self.timer = calvinsys.open(self, "sys.timer.once")
        calvinsys.write(self.timer, 10) # Wait a while

    def did_migrate(self):
        self.setup()
    
    def will_end(self):
        _log.info("Shutting down, received: {}, sent: {}".format(self.received, self.sent))
        # Note: This may cause some data to arrive out-of-order
        
        # move outgoing to (head of) incoming
        # print ("pre: {}".format(self.incoming))
        self.incoming.extend(self.outgoing)
        # print ("post: {}".format(self.incoming))
        # buffer to disk
        self.buffer_to_disk()
        # and end
        
    def buffer_to_disk(self):
        fifo = None
        if len(self.incoming) == 0:
            return
        try:
            fifo = calvinlib.use("filequeue").new(self.buffer_name)            
            while len(self.incoming) > 0:
                data = [ self.incoming.pop() for _ in range(min(len(self.incoming), self.buffer_limit))]
                fifo.push(self.json.tostring(data))
            fifo.close()
            self.uses_external = True
        except Exception as e:
            _log.info("Error buffering to disk: {}".format(e))

    def disk_to_buffer(self):
        fifo = None
        try:
            fifo = calvinlib.use("filequeue").new(self.buffer_name)
            while len(fifo) > 0 and len(self.outgoing) < self.buffer_limit:
                data = self.json.fromstring(fifo.pop())
                # print("to buffer: {}".format(data))
                self.outgoing.extendleft(data)
            self.uses_external = (len(fifo) != 0)
            fifo.close()
        except Exception as e:
            _log.info("Error reading from disk: {}".format(e))

    @stateguard(lambda self: calvinsys.can_read(self.timer))
    @condition([], [])
    def logger(self):
        calvinsys.read(self.timer)
        _log.info("incoming: {}, outgoing: {}, data stored: {}".format(
            self.received, self.sent, "yes" if self.uses_external else "no"))
        calvinsys.write(self.timer, self.interval)
    
    @condition(['data'], [])
    def receive(self, data):
        if data is not None:
            self.received += 1
            self.incoming.appendleft(data)

    @stateguard(lambda self: len(self.incoming) > 0 or self.uses_external)
    @condition([], [])
    def buffer_data(self):
        if not self.uses_external:
            self.outgoing.appendleft(self.incoming.pop())
        else:
            self.buffer_to_disk()
            self.disk_to_buffer()

    @stateguard(lambda self: len(self.outgoing) > 0)
    @condition([], ['data'])
    def send(self):
        self.sent += 1
        data = self.outgoing.pop()
        return (data,)

    action_priority = (logger, send, receive, buffer_data)
    
    requires = ['filequeue', 'queue', 'json', 'sys.timer.once']