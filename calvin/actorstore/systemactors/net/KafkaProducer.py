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

from calvin.actor.actor import Actor, manage, condition

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

class KafkaProducer(Actor):
    """
    Send all incoming messages to kafka. Will wait for acknowledgement after each token. The incoming data is assumed
    to be a dictionary with at least two fields 'calvints' and 'tag' where 'tag' is the key of the message, and
    'calvints' (milliseconds since epoch) is the timestamp.
    

    Arguments:
      bootstrap_servers: list of strings '<ip:port>' for bootstrapping kafka cluster.

    input:
      data: data to send
    """
    @manage(['bootstrap_servers', 'received', 'topic'])
    def init(self, bootstrap_servers, topic):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.received = 0
        self.setup()

    def setup(self):
        self.use('calvinsys.native.python-kafka', shorthand='kafka')
        self.use('calvinsys.native.python-json', shorthand='json')
        def serialize(data):
            return self['json'].dumps(data).encode('utf-8')
        self.producer = self['kafka'].producer(bootstrap_servers=self.bootstrap_servers,
                value_serializer=serialize, linger_ms=500, client_id="calvin-erdc")

    @condition(['data'], [])
    def receive(self, data):
        self.received += 1
        if self.received % 1000 == 0:
            _log.debug("{} values received".format(self.received))

        key = str(data['tag'])
        timestamp_ms = data.get('calvints', None)
        data.pop('endpoint') # not interesting, probably
        self.producer.send(topic=self.topic, key=key, value=data, timestamp_ms=timestamp_ms)
        return ()

    action_priority = (receive,)
    requires = ['calvinsys.native.python-kafka', 'calvinsys.native.python-json']
