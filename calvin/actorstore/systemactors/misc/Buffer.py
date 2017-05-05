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
    
    @manage(['num_tokens', 'buffer_name'])
    def init(self, num_tokens, buffer_name):
        _log.info("init buffer")
        self.num_tokens = num_tokens
        self.buffer_name = buffer_name
        self.setup()

    def setup(self):
        self.uses_external = True
        self.use(Buffer.requires[0], shorthand="collections")
        self.use(Buffer.requires[1], shorthand="filequeue")
        self.use(Buffer.requires[2], shorthand="json")
        self.buffer = self['collections'].deque()
    
    def did_migrate(self):
        self.setup()

    def will_migrate(self):
        # probably not a good idea unless buffer is empty
        pass
        
    def will_end(self):
        # write buffer to disk, then exit
        _log.info("flushing buffers ({} items)".format(len(self.buffer)))
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
        _log.info("done")
    
    @stateguard(lambda actor: len(actor.buffer) == 0 and not actor.uses_external)
    @condition(['data'], ['data'])
    def passthrough(self, data):
        return (data, )

    @condition(['data'], [])
    def buffer_data(self, data):
        self.buffer.append(data)
        if len(self.buffer) > 2*self.num_tokens:
            _log.info("buffer to file")
            fifo = None
            try:
                fifo = self['filequeue'].fifo(self.buffer_name)
                for i in range(self.num_tokens):
                    data = self.buffer.popleft()
                    fifo.push(self['json'].dumps(data))
                self.uses_external = True
            finally:
                if fifo: fifo.close()

    @stateguard(lambda actor: len(actor.buffer) > 0)
    @condition([], ['data'])
    def send_buffer(self):
        return (self.buffer.popleft(),)

    @stateguard(lambda actor: actor.uses_external and len(actor.buffer) < actor.num_tokens)
    @condition([], [])
    def read_buffer(self):
        _log.info("start - disk to buffer ({} items in buffer)".format(len(self.buffer)))
        fifo = None
        try:
            fifo = self['filequeue'].fifo(self.buffer_name)
            while len(fifo) and len(self.buffer) < self.num_tokens:
                data = fifo.pop()
                self.buffer.append(self['json'].loads(data))
            if len(fifo) == 0:
                self.uses_external = False
            fifo.close()
            fifo = None
        finally:
            if fifo: fifo.close()
        _log.info("end - disk to buffer ({} items in buffer)".format(len(self.buffer)))
        
    action_priority = (send_buffer, read_buffer, passthrough, buffer_data)
    
    requires = ['calvinsys.native.python-collections', 'calvinsys.native.python-filequeue', 'calvinsys.native.python-json']