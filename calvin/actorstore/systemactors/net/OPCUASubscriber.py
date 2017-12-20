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

from calvin.actor.actor import Actor, manage, condition, stateguard

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class OPCUASubscriber(Actor):
    """
    An OPCUA Client. Connects to given OPCUA server and sets up subscriptions for given parameters.

    Configuration input is of the form:
    {
      "origin": <mnemonic or similar identifying the origin, e.g. machine>,
      "namespace": <namespace number>,
      "parameters": {
        "<tag>" : {"address": "<address>", "info": "<description>"}
        ...
      }

    }

    Variable output is of the form (sample values given)
    {
        "id": "ns=2;s=/Channel/Parameter/rpa[u1,115]",
        "origin": "IM-1",
        "tag": "R115",
        "type": "Double",
        "value": "0.0",
        "serverts": "2017-03-20 15:42:41.600000",
        "sourcets": "2017-03-20 15:42:41.542000",
        "calvints": 1490021096110,
        "status": "0, Good, The operation completed successfully."
        "info": "description given for parameter"
    }

    Note: calvints is time in ms since epoch and is always present. Other timestamps may or may not
    be present depending on OPCUA server.

    Output:
        variable : list of changed variables on the format described above.
    """

    @manage(['endpoint', 'parameters', 'namespace', 'changed_params', 'client_config', 'origin'])
    def init(self, endpoint, config):
        self.endpoint = endpoint
        self.namespace = config.get("namespace", 2)
        self.parameters= config["parameters"]
        self.origin = config.get("origin", "N/A")
        self.client_config = config.get("client_configuration")
        self.changed_params = []
        self.setup()

    def did_migrate(self):
        self.setup()

    def will_end(self):
        self['opcua'].shutdown()

    def setup(self):
        self.tags = { str("ns=%d;s=%s" % (self.namespace, tag_value["address"])) : str(tag) for tag, tag_value in self.parameters.items() }
        self.use('calvinsys.opcua.client', shorthand='opcua')
        if self.client_config:
            self['opcua'].configure(self.client_config)
        self['opcua'].start_subscription(self.endpoint, self.tags.keys())
        self._report = False
        self._received = 0
        self._sent = 0
        print(self.tags)


    @stateguard(lambda self: self['opcua'].variable_changed)
    @condition()
    def changed(self):
        while self['opcua'].variable_changed:
            try:
                variable = self['opcua'].get_first_changed()
                variable["origin"] = self.origin
                variable["tag"] = self.tags[variable["id"]]
                variable["info"] = self.parameters[variable["tag"]]["info"]
                self.changed_params.append(variable)
                self._received += 1
            except Exception as e:
                _log.info("Failed to fetch variable: {}".format(e))
            if self._received % 10000 == 0:
                _log.info(" - changed - {} received, {} sent, {} queued".format(self._received, self._sent, len(self.changed_params)))
        return ()

    @stateguard(lambda actor: bool(actor.changed_params))
    @condition(action_output=['variable'])
    def handle_changed(self):
        variables = self.changed_params
        self.changed_params = []
        self._sent += len(variables)
        return (variables,)

    action_priority = (handle_changed, changed)
    requires = ['calvinsys.opcua.client']
