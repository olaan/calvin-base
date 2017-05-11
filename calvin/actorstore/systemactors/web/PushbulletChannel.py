# -*- coding: utf-8 -*-

# Copyright (c) 2016 Ericsson AB
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


class PushbulletChannel(Actor):
    """
    Push incoming data to a pushbullet channel. Data should be a text string. Requires pushbullet api-key in runtime.

    Input:
      title : title of message
      note : a message
    """

    @manage(['channel_name'])
    def init(self, channel):
        self.channel_name = channel
        self.setup()

    def did_migrate(self):
        self.setup()
 
    def setup(self):
        self.use('calvinsys.web.pbullet', shorthand='pbullet')
        self.channel = self['pbullet'].get_channel(self.channel_name)

    @condition(action_input=['title', 'note'])
    def note(self, title, note):
        self['pbullet'].push_to_channel(self.channel, title, note)
        

    action_priority = (note,)
    requires = ['calvinsys.web.pbullet']
