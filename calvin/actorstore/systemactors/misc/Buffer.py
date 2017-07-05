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

from calvin.actor.actor import Actor, manage, condition, stateguard
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class Buffer(Actor):
    """
    Buffer data to file if necessary.
    Inputs:
      data : some data

    Outputs:
        data : the same data
    """
    
    @manage(['num_tokens', 'buffer_name', 'sent', 'received', 'quiet'])
    def init(self, num_tokens, buffer_name, quiet=False):
        self.num_tokens = num_tokens
        self.buffer_name = buffer_name
        self.received = 0
        self.sent = 0
        self.quiet = quiet
        self.setup()

    def setup(self):
        self.uses_external = True # always check for disk data
        self.use(Buffer.requires[0], shorthand="collections")
        self.use(Buffer.requires[1], shorthand="filequeue")
        self.use(Buffer.requires[2], shorthand="json")
        self.use(Buffer.requires[3], shorthand="timer")
        self.buffer = self['collections'].deque()
        
        if self.quiet :
            self.timer = self['timer'].once(0) # show a bit of log at the start
            self.logger = _log.debug
        else :
            self.timer = None
            self.logger = _log.info
    
    def did_migrate(self):
        self.setup()

    def will_migrate(self):
        # probably not a good idea unless buffer (incl disk) is empty
        pass
        
    def will_end(self):
        # write buffer to disk, then exit
        self.logger("flushing buffers ({} items)".format(len(self.buffer)))
        if len(self.buffer) > 0:
            fifo = None
            try:
                fifo = self['filequeue'].fifo(self.buffer_name)
                while len(self.buffer) > 0:
                    data = self.buffer.popleft()
                    fifo.push(self['json'].dumps(data))
                fifo.close()
                fifo = None
            finally:
                if fifo: fifo.close()
        self.logger("done")
    
    
    def incoming(self):
        self.received += 1
        if self.received % (self.num_tokens/2) == 0:
            self.logger("recieved: {}, sent: {}, memory buffer: {}".format(self.received, self.sent, len(self.buffer)))
    
    def outgoing(self):
        self.sent += 1
        if self.sent % (self.num_tokens/2) == 0:
            self.logger("recieved: {}, sent: {}, memory buffer: {}".format(self.received, self.sent, len(self.buffer)))


    @stateguard(lambda actor: actor.timer and actor.timer.triggered)
    @condition()
    def flip_logging(self):
        self.timer.ack()
        if self.quiet:
            self.quiet = False
            self.logger = _log.info
            self.timer = self['timer'].once(60)
        else :
            self.quiet = True
            self.logger = _log.debug
            self.timer = self['timer'].once(600)

        
    @stateguard(lambda actor: len(actor.buffer) == 0 and not actor.uses_external)
    @condition(['data'], ['data'])
    def passthrough(self, data):
        self.incoming()
        self.outgoing()
        return (data, )

    @condition(['data'], [])
    def buffer_data(self, data):
        self.incoming()
        self.buffer.append(data)
        if len(self.buffer) > 3*self.num_tokens:
            fifo = None
            try:
                fifo = self['filequeue'].fifo(self.buffer_name)
                data = []
                while len(self.buffer) > self.num_tokens:
                    data = self.buffer.popleft()
                    fifo.push(self['json'].dumps(data))
                self.uses_external = True
            finally:
                if fifo:
                    self.logger("buffer to file -  {} items total stored".format(len(fifo)))
                    fifo.close()
            

    @stateguard(lambda actor: len(actor.buffer) > 0)
    @condition([], ['data'])
    def send_buffer(self):
        self.outgoing()
        return (self.buffer.popleft(),)

    @stateguard(lambda actor: actor.uses_external and len(actor.buffer) < actor.num_tokens)
    @condition([], [])
    def read_buffer(self):
        fifo = None
        try:
            fifo = self['filequeue'].fifo(self.buffer_name)
            while len(fifo) and len(self.buffer) < 2*self.num_tokens:
                data = fifo.pop()
                self.buffer.append(self['json'].loads(data))
            if len(fifo) == 0:
                self.uses_external = False
        finally:
            if fifo: 
                self.logger("disk to buffer - {} items in buffer, {} total stored".format(len(self.buffer), len(fifo)))
                fifo.close()

    action_priority = (flip_logging, send_buffer, read_buffer, passthrough, buffer_data)
    
    requires = ['calvinsys.native.python-collections', 'calvinsys.native.python-filequeue', 'calvinsys.native.python-json', 'calvinsys.events.timer']