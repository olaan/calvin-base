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

from calvin.actor.actor import Actor, manage, condition
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class TokenCounter(Actor):
    """
    Counts tokens as they arrive
    Input:
      token : Anything token
    """

    def exception_handler(self, action, args, context):
        # Check args to verify that it is EOSToken
        return action(self, *args)

    @manage(['ctr', 'checkpoint', 'origin'])
    def init(self, origin, checkpoint):
        self.ctr = 0
        self.origin = origin
        self.checkpoint = checkpoint
        self.setup()

    def did_migrate(self):
        self.setup()

    def setup(self):
        self.logger = _log.info

    @condition(action_input=['token'])
    def count(self, token):
        self.ctr += 1
        if self.ctr % self.checkpoint == 0 :
            _log.info("{}: {} tokens received".format(self.origin, self.ctr))

    action_priority = (count, )