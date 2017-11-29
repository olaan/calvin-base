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

class SqliteQueueAsync(BaseQueue.BaseQueue):
    """
    Asynchronous (using twisted adbapi) SQLite-based implementation of persistant queue
    
    Based on the following (from sqlite.org):
      1)  If no ROWID is specified on the insert [...] then an appropriate ROWID is created automatically.
      2) The usual algorithm is to give the newly created row a ROWID that is one larger than the largest
         ROWID in the table prior to the insert.
      3) If the table is initially empty, then a ROWID of 1 is used.
      4) If the largest ROWID is equal to the largest possible integer (9223372036854775807) then the
        database engine starts picking positive candidate ROWIDs at random until it finds one
        that is not previously used.
      5) The normal ROWID selection [...] will generate monotonically increasing unique ROWIDs as long
        as you never use the maximum ROWID value and you never delete the entry in the table with the largest ROWID.

    Since we are implementing a FIFO queue, 1) should ensure there is a row id, 2) & 5) that the ordering is correct
    and 3) that the rowid is reset whenever the queue is emptied, so 4) should never happen.
    """
    
    def init(self, **kwargs):
        self.db_name = kwargs.get("queue_id", "db")
        self.db_path = os.path.join(os.path.abspath(os.path.curdir), self.db_name + ".sq3")
        self.db = adbapi.ConnectionPool('sqlite3', self.db_path, check_same_thread=False)
        
        self._value = None
        self._changed = None

        def ready(length):
            self._changed = True # Something has changed, need to check if readable
            self.scheduler_wakeup()

        def create(db):
            # Create simple queue table. Using TEXT unless there is a reason not to.
            db.execute("CREATE TABLE IF NOT EXISTS queue (value BLOB)")

        def error(e):
            _log.error("Error initializing queue {}: {}".format(self.db_name, e))

        q = self.db.runInteraction(create)
        q.addCallback(ready)
        q.addErrback(error)

        
    def can_write(self):
        # Can always write after init, meaning changed is no longer None
        return self._changed is not None

    def write(self, value):
        def error(e):
            _log.warning("Error during write: {}".format(e))
            done() # Call done to wake scheduler, not sure this is a good idea
            
        def done(unused=None):
            self._changed = True # Let can_read know there may be something new to read
            self.scheduler_wakeup()

        value = json.dumps(value) # Convert to string for sqlite
        q = self.db.runOperation("INSERT INTO queue (value) VALUES (?)", (value, ))
        q.addCallback(done)
        q.addErrback(error)


    def can_read(self):
        def error(e):
            _log.warning("Error during read: {}".format(e))
            done()
            
        def done(value=None):
            if value is not None:
                self._changed = True # alser can_read that the database has changed
                self._value = json.loads(value)
            self.scheduler_wakeup()

        def pop(db):
            db.execute("SELECT value FROM queue ORDER BY rowid LIMIT 1")
            value = db.fetchone() # a (idx, value) tuple, or None
            if value is not None:
                value = value[0]
                # pop value (i.e. delete row with lowest row id)
                db.execute("DELETE FROM queue WHERE rowid = (SELECT rowid FROM queue ORDER BY rowid LIMIT 1)")

            return value

        if self._value is not None:
            # There is a value to read
            return True
        elif self._changed :
            # Something has changed, try to pop a value
            self._changed = False
            q = self.db.runInteraction(pop)
            q.addCallback(done)
            q.addErrback(error)

        # Nothing to do
        return False

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

