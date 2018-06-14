# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from rally.common import cfg


KUBERNETES_OPTS = [
    cfg.FloatOpt("start_prepoll_delay",
                 default=0.0,
                 help="Time to sleep before polling for status"),
    cfg.IntOpt("status_total_retries",
               default=50,
               help="Kubernetes total retries to read resource status"),
    cfg.FloatOpt("status_poll_interval",
                 default=1.0,
                 help="Kubernetes status poll interval")
]


def list_opts():
    """Return a list of configuration options.

    This is entry-point which is configured via setup.cfg
    """

    return {"kubernetes": KUBERNETES_OPTS}
