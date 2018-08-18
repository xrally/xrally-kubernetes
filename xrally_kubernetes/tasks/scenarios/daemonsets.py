# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from rally.task import scenario

from xrally_kubernetes.tasks import scenario as common_scenario


@scenario.configure("Kubernetes.create_check_and_delete_daemonset",
                    platform="kubernetes")
class CreateCheckAndDeleteDaemonSet(common_scenario.BaseKubernetesScenario):

    def run(self, image, command=None, node_labels=None, status_wait=True):
        """Create daemonSet, check it's pods on each node and delete it then.

        Create daemonSet, check it's pods on each node (optionally filter nodes
        with node_labels map) and delete daemonSet then.

        :param image: daemon set template image
        :param command: daemon set template command
        :param node_labels: map of labels, by which nodes would be filtered
        :param status_wait: wait for status if True
        """
        namespace = self.choose_namespace()

        name, app = self.client.create_daemonset(
            image=image,
            namespace=namespace,
            command=command,
            node_labels=node_labels,
            status_wait=status_wait
        )
        self.client.check_daemonset(
            namespace=namespace,
            app=app,
            node_labels=node_labels
        )
        self.client.delete_daemonset(
            name,
            namespace=namespace,
            status_wait=status_wait
        )
