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


class NoSink(Actor):
    """
    A sink which never accepts a token


    For testing purposes only. Unlikely to be of real use.

    Inputs:
      void : A port that will never consume a token
    """
    @manage(["accept", "delay", "received"])
    def init(self, delay):
        self.accept = False
        self.delay = delay
        self.received = 0
        self.setup()

    def did_migrate(self):
        self.setup()
        
    def setup(self):
        self.use("calvinsys.events.timer", shorthand="timer")
        self.use("calvinsys.math.rng", shorthand="random")
        if self.delay > 0:
            self.timer = self['timer'].once(self.delay)
    
    @stateguard(lambda actor: actor.accept)
    @condition(['void'], [])
    def consume(self, data):
        self.received += 1
        print("{}: {}".format(self.received, data))
        return ()

    @stateguard(lambda actor: actor.timer.triggered)
    @condition([], [])
    def start(self):
        _log.info("flip")
        self.accept = not self.accept
        self.timer = self['timer'].once(self["random"].randrange(3, 8))
        return ()
        
    action_priority = (consume, start)
    
    requires = ['calvinsys.events.timer', 'calvinsys.math.rng']

