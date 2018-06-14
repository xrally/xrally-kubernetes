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


@scenario.configure(name="Kubernetes.list_namespaces", platform="kubernetes")
class ListNamespaces(common_scenario.BaseKubernetesScenario):
    """List cluster namespaces."""

    def run(self):
        """List cluster namespaces."""
        namespaces = self.client.list_namespaces()
        if namespaces:
            self.add_output(
                complete={
                    "title": "Namespaces",
                    "description": "A list of available namespaces.",
                    "chart_plugin": "Table",
                    "data": {
                        "cols": ["Name", "UID", "Labels"],
                        "rows": [[ns["name"], ns["uid"], ns["labels"]]
                                 for ns in namespaces]
                    }
                }
            )
        else:
            self.add_output(
                complete={
                    "title": "Namespaces",
                    "chart_plugin": "TextArea",
                    "data": ["No namespaces are available."]})


@scenario.configure(name="Kubernetes.create_and_delete_namespace",
                    platform="kubernetes")
class CreateAndDeleteNamespace(common_scenario.BaseKubernetesScenario):

    def run(self, name=None, status_wait=True):
        """Create namespace, wait until it won't be active and then delete it.

        :param name: namespace custom name
        :param status_wait: wait namespace status after creation
        """
        name = self.client.create_namespace(name, status_wait=status_wait)
        self.client.delete_namespace(name, status_wait=status_wait)
