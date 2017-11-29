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
from twisted.enterprise import adbapi
import os.path

import json

_log = get_logger(__name__)

def errored(*args, **kwargs):
    _log.info("ERROR: {} / {}".format(args, kwargs))
    
class SqliteQueueAsync(BaseQueue.BaseQueue):
    """
    Asynchronous (using twisted adbapi) SQLite-based implementation of persistant queue
        """
    
    def init(self, **kwargs):
        self.db_name = kwargs.get("queue_id", "db")
        self.db_path = os.path.join(os.path.abspath(os.path.curdir), self.db_name)
        self.db = adbapi.ConnectionPool('sqlite3', self.db_path, check_same_thread=False)
        
        self._readlock = True
        self._value = None

        def ready(arg):
            self._readlock = False
            self.scheduler_wakeup()

        def create(db):
            db.execute("CREATE TABLE IF NOT EXISTS queue (id INTEGER PRIMARY KEY AUTOINCREMENT, value BLOB)")
            
        q = self.db.runInteraction(create)
        q.addCallback(ready)
        q.addErrback(errored)

        
    def can_write(self):
        return True

    def write(self, value):
        def error(*args):
            _log.warning("Error during write: {}".format(args))
            done()
            
        def done(_):
            self.scheduler_wakeup()

        value = json.dumps(value)
        q = self.db.runOperation("INSERT INTO queue (value) VALUES (?)", (value, ))
        q.addCallback(done)
        q.addErrback(error)


    def can_read(self):
        def error(*args):
            _log.warning("Error during read: {}".format(args))
            done(None)
            
        def done(value):
            self._readlock = False
            if value:
                self._value = json.loads(value)
            # _log.info("returning new value {}".format(value))
            self.scheduler_wakeup()

        def pop(db):
            db.execute("SELECT id, value FROM queue ORDER BY id LIMIT 1")
            res = db.fetchone()
            # _log.info("popped: {}".format(res))
            value = None
            if res:
                idx, value = res
                db.execute("DELETE FROM queue WHERE id = ?", (idx,))
            return value

        if not self._readlock :
            self._readlock = True
            q = self.db.runInteraction(pop)
            q.addCallback(done)
            q.addErrback(errored)

        return self._value is not None

    def read(self):
        value = self._value
        # _log.info("value : {}".format(self._value))
        self._value = None
        return value

    def close(self):
        def done(response):
            # A count response; [(cnt,)]
            if response[0][0] == 0:
                try:
                    os.remove(self.
                    db_path)
                except:
                    # Failed for some reason
                    _log.warning("Could not remove db file {}".format(self._dbpath))
        q = self.db.runQuery("SELECT COUNT(*) from queue")
        q.addCallback(done)
        self.db.close()

