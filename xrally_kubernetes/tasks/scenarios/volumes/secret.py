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

from xrally_kubernetes.tasks.scenarios.volumes import base


@scenario.configure(
    name="Kubernetes.create_and_delete_pod_with_secret_volume",
    platform="kubernetes"
)
class CreateAndDeletePodWithSecretVolume(base.PodWithVolumeBaseScenario):

    def run(self, image, mount_path, check_cmd=None, error_regexp=None,
            command=None, status_wait=True):
        """Create pod with secret volume, optionally check and delete then.

        Create secret, create pod with secret volume, optionally wait for it's
        readiness, check volume existence by check_cmd, if it defined and
        delete pod and secret then.

        :param image: pod's image
        :param mount_path: path to mount volume in pod
        :param check_cmd: check command to exec in pod; if None, then no check
        :param error_regexp: regexp string to search error in pod exec response
        :param command: array of strings representing container command
        :param status_wait: wait pod status for success if True
        """
        name = self.generate_random_name()

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
                    "secret": {
                        "secretName": name
                    }
                }
            ]
        }

        self.client.create_secret(name, namespace=self.namespace)

        super(CreateAndDeletePodWithSecretVolume, self).run(
            image,
            name=name,
            command=command,
            check_cmd=check_cmd,
            error_regexp=error_regexp,
            volume=volume,
            status_wait=status_wait
        )

        self.client.delete_secret(name, namespace=self.namespace)
