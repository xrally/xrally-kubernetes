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
from rally.task import validation

from xrally_kubernetes.tasks import scenario as common_scenario


@scenario.configure(name="Kubernetes.create_and_delete_deployment",
                    platform="kubernetes")
class CreateAndDeleteDeployment(common_scenario.BaseKubernetesScenario):
    """Kubernetes deployment create and delete test.

    Choose created namespace, create deployment with defined image and number
    of replicas, wait until it won't be running and delete it after.
    """

    def run(self, image, replicas, command=None, status_wait=True):
        """Create and delete deployment and wait for status optionally.

        :param image: container's template image
        :param replicas: number of replicas for deployment
        :param status_wait: wait for full status if True
        :param command: array of strings representing container command
        """
        namespace = self.choose_namespace()

        name = self.client.create_deployment(
            replicas=replicas,
            image=image,
            namespace=namespace,
            command=command,
            status_wait=status_wait
        )

        self.client.delete_deployment(
            name,
            namespace=namespace,
            status_wait=status_wait
        )


@validation.add("map_keys", param_name="changes",
                allowed=["image", "env", "resources"])
@scenario.configure(name="Kubernetes.create_rollout_and_delete_deployment",
                    platform="kubernetes")
class CreateRolloutAndDeleteDeployment(common_scenario.BaseKubernetesScenario):
    """Kubernetes deployment rollout test.

    Create deployment, rollout deployment with some args and delete it then.
    """

    def run(self, image, replicas, changes, command=None,
            env=None, resources=None, status_wait=True):
        """Create deployment, rollout with some changes and then delete it.

        :param image: deployment pod template image
        :param replicas: original number of replicas
        :param changes: map of changes, where could be image, env or resources
               requirements
        :param resources: container's template resources requirements
        :param env: container's template env variables array
        :param command: array of strings representing container command
        :param status_wait: wait for full status if True
        """
        namespace = self.choose_namespace()

        name = self.client.create_deployment(
            namespace=namespace,
            replicas=replicas,
            image=image,
            command=command,
            env=env,
            resources=resources,
            status_wait=status_wait
        )

        self.client.rollout_deployment(
            name,
            namespace=namespace,
            replicas=replicas,
            changes=changes,
            status_wait=status_wait
        )

        self.client.delete_deployment(
            name=name,
            namespace=namespace,
            status_wait=status_wait
        )
