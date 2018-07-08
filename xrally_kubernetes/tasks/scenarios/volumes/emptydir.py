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


@scenario.configure(name="Kubernetes.create_and_delete_emptydir_volume",
                    platform="kubernetes")
class CreateAndDeleteEmptyDirVolume(common_scenario.BaseKubernetesScenario):

    def run(self, image, mount_path, name=None, command=None,
            status_wait=True):
        """Create pod with emptyDir volume, wait it readiness and delete then.

        :param image: pod's image
        :param mount_path: path to mount volume in pod
        :param name: custom pod's name
        :param command: array of strings representing container command
        :param status_wait: wait pod status for success if True
        """
        name = name or self.generate_random_name()
        namespace = self.choose_namespace()

        volume = {
            "mount_path": [
                {
                    "mountPath": mount_path,
                    "name": name
                }
            ],
            "volume": [
                {
                    "name": name,
                    "emptyDir": {}
                }
            ]
        }

        name = self.client.create_pod(
            name,
            image=image,
            volume=volume,
            namespace=namespace,
            command=command,
            status_wait=status_wait
        )

        self.client.delete_pod(
            name,
            namespace=namespace,
            status_wait=status_wait
        )


@scenario.configure(name="Kubernetes.create_check_and_delete_emptydir_volume",
                    platform="kubernetes")
class CreateCheckDeleteEmptyDirVolume(common_scenario.BaseKubernetesScenario):

    def run(self, image, mount_path, check_cmd, name=None, command=None,
            error_regexp=None, status_wait=True):
        """Create pod with emptyDir volume, wait it readiness and delete then.

        :param image: pod's image
        :param mount_path: path to mount volume in pod
        :param check_cmd: check command to exec in pod
        :param name: pod's custom name
        :param command: array of strings representing container command
        :param error_regexp: regexp string to search error in pod exec response
        :param status_wait: wait pod status for success if True
        """
        name = name or self.generate_random_name()
        namespace = self.choose_namespace()

        volume = {
            "mount_path": [
                {
                    "mountPath": mount_path,
                    "name": name
                }
            ],
            "volume": [
                {
                    "name": name,
                    "emptyDir": {}
                }
            ]
        }

        name = self.client.create_pod(
            name,
            image=image,
            volume=volume,
            namespace=namespace,
            command=command,
            status_wait=status_wait
        )

        self.client.check_volume_pod(
            name,
            namespace=namespace,
            check_cmd=check_cmd,
            error_regexp=error_regexp
        )

        self.client.delete_pod(
            name,
            namespace=namespace,
            status_wait=status_wait
        )
