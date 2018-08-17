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

from xrally_kubernetes.tasks import scenario as common_scenario


class PodWithVolumeBaseScenario(common_scenario.BaseKubernetesScenario):
    """Base scenario plugin for all pod with volume scenarios."""

    def __init__(self, context=None):
        super(PodWithVolumeBaseScenario, self).__init__(context)
        self.namespace = self.choose_namespace()

    def run(self, image, name=None, check_cmd=None, command=None,
            error_regexp=None, volume=None, status_wait=True):
        """Super class for all kubernetes pod with volume scenarios.

        :param image: pod's image
        :param name: pod's name, equals to volume name
        :param check_cmd: pod exec command, available if volume_check is True
        :param command: pod container's command
        :param error_regexp: regexp string to search error in pod exec
               response, available if volume_check is True
        :param volume: a dict, which contains `mount_path` and `volume` keys
               with parts of pod's manifest as values
        :param status_wait: wait for pod's status if True
        """
        name = self.client.create_pod(
            image,
            name=name,
            volume=volume,
            namespace=self.namespace,
            command=command,
            status_wait=status_wait
        )

        if check_cmd:
            self.client.check_volume_pod(
                name,
                namespace=self.namespace,
                check_cmd=check_cmd,
                error_regexp=error_regexp
            )

        self.client.delete_pod(
            name,
            namespace=self.namespace,
            status_wait=status_wait
        )
