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

from calvin.runtime.south.calvinsys.data.queue import BaseQueue
from calvin.utilities.calvinlogger import get_logger
from collections import deque

_log = get_logger(__name__)

class DequeQueue(BaseQueue.BaseQueue):
    """
    Deque implementation of in-memory queue
    """
    
    def init(self, **kwargs):
        self.queue = deque()

    def can_write(self):
        return True

    def write(self, value):
        self.queue.append(value)

    def can_read(self):
        return len(self.queue) != 0

    def read(self):
        return self.queue.pop()

    def close(self):
        del self.queue
