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


class SystemLog(Actor):
    """
    Retrieve n latest entries in system log for given service
    Inputs:
      trigger: trigger fetching

    Outputs:
        entries: String containing entries - one per line
    """
    
    @manage(['service', 'num_entries'])
    def init(self, service, num_entries):
        self.service = service
        self.num_entries = num_entries
        self.setup()

    def setup(self):
        self.use(SystemLog.requires[0], shorthand="journal")
        self.journal=self["journal"]
    
    def did_migrate(self):
        self.setup()

    def will_migrate(self):
        pass

    @condition(['trigger'], ['entries'])
    def retrieve(self, data):
        entries = self.journal.get_latest(self.service, self.num_entries)
        data = "\n".join(e for e in entries)
        return (data,)

    action_priority = (retrieve,)
    
    requires = ['calvinsys.native.python-systemd']
