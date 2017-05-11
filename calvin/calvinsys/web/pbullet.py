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

from calvin.runtime.south.plugins.web import pbullet
from calvin.utilities.calvinlogger import get_logger


_log = get_logger(__name__)


class Pushbullet(object):
    """
        A calvinsys module for sending notes via pushbullet. Requires api key credentials of the form
        { 
            "api_key" : "<api key">
        }
        
        The credentials are added either as a private runtime attribute, i.e
        
        /private/web/pushbullet.com/
        
        or supplied by the actor before trying to send messages, i.e.
        
        actor.use('calvinsys.web.pbullet', shorthand='pbullet')
        actor['pbullet'].set_credentials({...})
        
        Note: Currently, credentials can only be supplied once and cannot be changed once in use.
    """
    
    def __init__(self, node, actor):
        self._node = node
        self._actor = actor
        
        credentials = self._node.attributes.get_private("/web/pushbullet.com")
        if credentials:
            self._pbullet = pbullet.Pushbullet(credentials)
        else :
            _log.warning("Expected credentials /private/web/pushbullet.com not found")
            self._pbullet = None
            
    def set_credentials(self, api_key):
        if not self._pbullet:
            self._pbullet = pbullet.PushBullet(api_key)
            success = True
        else :
            _log.warning("Credentials already supplied - ignoring")
            success = False
        return success
    
    def get_channel(self, channel_name):
        return self._pbullet.get_channel(channel_name)
    
    def push_to_channel(self, channel, title, text):
        if not self._pbullet:
            _log.warning("Credentials not set, cannot send message")
            return
        self._pbullet.push_to_channel(channel, title, text)


def register(node, actor):
    return Pushbullet(node, actor)
