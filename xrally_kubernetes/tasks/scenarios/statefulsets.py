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


@scenario.configure(name="Kubernetes.create_and_delete_statefulset",
                    platform="kubernetes")
class CreateAndDeleteStatefulSet(common_scenario.BaseKubernetesScenario):
    """Kubernetes statefulset create and delete test.

    Choose created namespace, create statefulset with defined image and number
    of replicas, wait until it won't be running and delete it after.
    """

    def run(self, image, replicas, command=None, status_wait=True):
        """Create and delete statefulset and wait for status optionally.

        :param image: container's template image
        :param replicas: number of replicas for statefulset
        :param status_wait: wait for full status if True
        :param command: array of strings representing container command
        """
        namespace = self.choose_namespace()

        name = self.client.create_statefulset(
            replicas=replicas,
            image=image,
            namespace=namespace,
            command=command,
            status_wait=status_wait
        )

        self.client.delete_statefulset(
            name,
            namespace=namespace,
            status_wait=status_wait
        )


@scenario.configure(name="Kubernetes.create_scale_and_delete_statefulset",
                    platform="kubernetes")
class CreateScaleAndDeleteStatefulSet(common_scenario.BaseKubernetesScenario):
    """Kubernetes statefulset scale test.

    Create statefulset, scale it with number of replicas,
    scale it with original number of replicas, delete statefulset.
    """

    def run(self, image, replicas, scale_replicas, command=None,
            status_wait=True):
        """Create statefulset, scale for number of replicas and then delete it.

        :param image: statefulset pod template image
        :param replicas: original number of replicas
        :param scale_replicas: number of replicas to scale
        :param command: array of strings representing container command
        :param status_wait: wait for full status if True
        """
        namespace = self.choose_namespace()

        name = self.client.create_statefulset(
            namespace=namespace,
            replicas=replicas,
            image=image,
            command=command,
            status_wait=status_wait
        )

        self.client.scale_statefulset(
            name,
            namespace=namespace,
            replicas=scale_replicas,
            status_wait=status_wait
        )

        self.client.scale_statefulset(
            name,
            namespace=namespace,
            replicas=replicas,
            status_wait=status_wait
        )

        self.client.delete_statefulset(
            name=name,
            namespace=namespace,
            status_wait=status_wait
        )
