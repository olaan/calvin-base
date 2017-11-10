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

import opcua
import json

# FIXME: Uncomment to see OPCUA logs, will double all logging.
# import logging 
# logging.basicConfig()

from calvin.utilities.calvinlogger import get_logger
from calvin.runtime.south.plugins.async import threads, async

WATCHDOG_TIMEOUT = 60 # Reset connection if no data within 2 x WATCHDOG_TIMER seconds
RECONNECT_TIMER = 10 # Attempt reconnect every RECONNECT_TIMER seconds if connection lost
INTERVAL = 1000 # Interval to use in subscription check, probably ms


_log = get_logger(__name__)


def data_value_to_struct(data_value):
    def dt_to_ts(dt):
        import time
        import datetime
        if not dt:
            dt = datetime.datetime.now()
        try:
            res = str(time.mktime(dt.timetuple()))[:-2] + str(dt.microsecond/1000000.0)[1:]
        except Exception as e:
            _log.warning("Could not convert dt to timestamp: %r" % (e,))
            res = 0.0
        return res

    return {
        "type": data_value.Value.VariantType.name,
        "value": json.dumps(data_value.Value.Value),
        "status": { "code": data_value.StatusCode.value, 
                    "name": data_value.StatusCode.name,
                    "doc": data_value.StatusCode.doc
                },
        "sourcets": str(data_value.SourceTimestamp),
        "serverts": str(data_value.ServerTimestamp)
        }


def get_node_id_as_string(node):
    nodeid = str(node.nodeid)
    # nodeid is of the form (ns=X;s=XXX), remove parentheses
    nodeid = nodeid[nodeid.index('(')+1:nodeid.rindex(')')]
    return nodeid

class OPCUAClient(object):

    class SubscriptionHandler(object):
        def __init__(self, handler):
            super(OPCUAClient.SubscriptionHandler, self).__init__()
            self._handler = handler
            self._changes = 0

        def changes(self):
            return self._changes
            
        def reset_changes(self):
            self._changes = 0
            
        def notify_handler(self, node, variable):
            variable["id"] = get_node_id_as_string(node)
            # Note that something has changed (for the watchdog)
            self._changes += 1
            # hand the notification over to the scheduler
            self._handler(variable)

        def datachange_notification(self, node, val, data):
            self.notify_handler(node, data_value_to_struct(data.monitored_item.Value))

        def event_notification(self, event):
            _log.info("%r" % (event,))
            
    def __init__(self, endpoint, config):
        self._endpoint = endpoint
        self.nodeids = []
        self.subscription = None
        self._changed_variables = []
        self._running = False
        self._client = None
        self._handle = None
        self._reconnecting  = None
        self._resubscribing = None
        self._watchdog_runnng = None
        
        self._watchdog_timeout = config.get("watchdog_timeout", None) or WATCHDOG_TIMEOUT
        self._reconnect_timer = config.get("reconnect_timer", None) or RECONNECT_TIMER
        self._subscription_interval = config.get("subscription_interval", None) or INTERVAL
        
    
    def reconnect_in_progress(self):
        return self._reconnecting and self._reconnecting.active()
        
    def connect(self, notifier):
        if not self.reconnect_in_progress():
            self._connect(notifier)
    
    def _connect(self, notifier):
        # Should only ever be called when there is no connection in progress (i.e. reconnect_in_progress() is False)
        self._reconnecting = None
        self._client = opcua.Client(self._endpoint)
        d = threads.defer_to_thread(self._client.connect)
        d.addCallback(notifier)
        d.addErrback(self._retry_connect, notifier)
    
    def _retry_connect(self, failure, notifier):
        failtype = failure.type
        # Only retry if client has not been deleted (disconnected or migrated)
        if self._client:
            # Only start reconnection if not already doing so
            if not self.reconnect_in_progress():
                _log.info("Failed to connect, with reason {}, retrying in {}".format(failtype, self._reconnect_timer))
                self._reconnecting = async.DelayedCall(self._reconnect_timer, self._connect, notifier)
            else:
                _log.info("Reconnection in progress, not restarting")

    def disconnect(self):
        if self.subscription:
            async.call_in_thread(self.subscription.delete)
            self.subscription = None
            
        if self._client:
            async.call_in_thread(self._client.disconnect)
            self._client = None

    def _subscribe(self):

        def watchdog(self, subscription_handler, *args, **kwargs):
            if not self._client:
                # There is no client. This means either a reconnection, migration or shutdown is in progress.
                return

            if subscription_handler.changes() == 0:
                _log.warning("Data watchdog triggered for {}, resetting connection".format(self.endpoint))
                self._resubscribe()
            else:
                subscription_handler.reset_changes()
            self._watchdog_running.reset()

        def setup_subscription(*args, **kwargs):
            # Create subscription handler
            sub_handler = self.SubscriptionHandler(self.handler)
            # Create (empty) OPCUA subscription with subscription handler
            self.subscription = self._client.create_subscription(self._subscription_interval, sub_handler)
            # Collect variables (nodes) from client
            variables = []
            for node in self.nodeids:
                variable = None
                try:
                    variable = self._client.get_node(node)
                except Exception as e:
                    _log.warning("Failed to get node {}: {}".format(node, e))
                if variable is not None:
                    variables.append(variable)
                    
            # Subscribe to changes in collected variables
            for v in variables:
                self.subscription.subscribe_data_change(v)
                
            # Should the list be empty, we let the watchdog handle it by resetting the subscription
            self._watchdog_running = async.DelayedCall(self._watchdog_timout, watchdog, sub_handler)

        def connection_done(*args, **kwargs):
            def subscription_error(self, failure):
                _log.warning("Failed to setup subscription for {} with reason {} - resetting connection".format(self.endpoint, failure.type))
                self._resubscribe()
            
            d = threads.defer_to_thread(setup_subscription)
            d.addErrback(subscription_error)
        
        self._resubscribing = None
        
        if self._client:
            # We already have a connection, just setup the subscription
            connection_done()
        else :
            # Connect and then setup subscription
            self.connect(connection_done)

    def _resubscribe(self):
        if not self._resubscribing:
            # Subscription issues often caused by connection problems, disconnect
            self.disconnect()
            self._resubscribing = async.DelayedCall(self._reconnect_timer, self._subscribe)
        
    def subscribe(self, nodeids, handler):
        # Save callback and nodeids before setting up subscription
        self.nodeids = nodeids
        self.handler = handler
        self._subscribe()
