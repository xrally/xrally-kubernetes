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
    name="Kubernetes.create_and_delete_pod_with_configmap_volume",
    platform="kubernetes"
)
class CreateAndDeletePodWithConfigMapVolume(base.PodWithVolumeBaseScenario):

    def run(self, image, mount_path, configmap_data, subpath=None,
            check_cmd=None, error_regexp=None, command=None, status_wait=True):
        """Create pod with configMap volume, optionally check and delete then.

        Create pod with configMap volume, optionally wait for it's readiness,
        check volume existence by check_cmd, if it defined and delete pod then.

        :param image: pod's image
        :param mount_path: path to mount volume in pod
        :param configmap_data: configMap resource data
        :param subpath: subPath from configMap data to mount in pod
        :param check_cmd: check command to exec in pod; if None, then no check
        :param error_regexp: regexp string to search error in pod exec response
        :param command: array of strings representing container command
        :param status_wait: wait pod status for success if True
        """
        name = self.generate_random_name()

        self.client.create_configmap(
            name,
            namespace=self.namespace,
            data=configmap_data
        )

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
                    "configMap": {
                        "name": name
                    }
                }
            ]
        }
        if subpath:
            volume["mount_path"][0]["subPath"] = subpath

        super(CreateAndDeletePodWithConfigMapVolume, self).run(
            image,
            name=name,
            command=command,
            check_cmd=check_cmd,
            error_regexp=error_regexp,
            volume=volume,
            status_wait=status_wait
        )

        self.client.delete_configmap(name, namespace=self.namespace)
