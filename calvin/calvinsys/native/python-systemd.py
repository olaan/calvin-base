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

from systemd import journal

class Journal(object):
    def get_latest(self, service, num_entries):
        j = journal.Reader()
        j.log_level(journal.LOG_INFO)
        j.add_match(_SYSTEMD_UNIT=u'{}'.format(service))
        j.seek_tail()
        entries = [j.get_previous()['MESSAGE'] for _ in range(num_entries) ]
        j.close()
        entries.reverse()
        return entries

def register(node=None, actor=None):
    return Journal()