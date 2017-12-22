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

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class AppIoTSubscribe(Actor):
    """
    Subscribe to AppIoT measurements

    Output:
        measurement : A measurement.
    """

    @manage([])
    def init(self, resource_ids):
        self.appiot = calvinsys.open(self, "data.appiot", resource_ids=resource_ids)

    @stateguard(lambda self: calvinsys.can_read(self.appiot))
    @condition([], ["measurement"])
    def send_data(self):
        return (calvinsys.read(self.appiot), )

    action_priority = (send_data,)
    requires = ['data.appiot']

