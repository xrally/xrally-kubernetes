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

from rally.task import atomic
from rally.task import scenario
from rally.task import validation

from xrally_kubernetes.tasks.scenarios.volumes import base


@validation.add("map_keys", param_name="persistent_volume",
                required=["size", "volume_mode", "local_path",
                          "access_modes", "node_affinity"])
@validation.add("map_keys", param_name="persistent_volume_claim",
                required=["size", "access_modes"])
@scenario.configure(
    name="Kubernetes.create_and_delete_pod_with_local_persistent_volume",
    platform="kubernetes"
)
class CreateAndDeletePodWithLocalPVVolume(base.PodWithVolumeBaseScenario):

    def run(self, image, mount_path, persistent_volume,
            persistent_volume_claim, check_cmd=None, error_regexp=None,
            command=None, status_wait=True):
        """Create pod with local PV, optionally check and delete then.

        Create pod with local persistent volume, optionally wait for it's
        readiness, check volume existence by check_cmd, if it defined and
        delete pod then.

        :param image: pod's image
        :param mount_path: path to mount volume in pod
        :param persistent_volume: a dict with the next keys: `size`,
               `volume_mode`, `local_path`, `access_modes`, `node_affinity`
        :param persistent_volume_claim: a dict with the next keys: `size` and
               `access_modes`
        :param check_cmd: check command to exec in pod; if None, then no check
        :param error_regexp: regexp string to search error in pod exec response
        :param command: array of strings representing container command
        :param status_wait: wait pod status for success if True
        """
        name = self.generate_random_name()

        self.client.create_local_pv(
            name,
            storage_class=self.context["kubernetes"]["storageclass"],
            size=persistent_volume["size"],
            volume_mode=persistent_volume["volume_mode"],
            local_path=persistent_volume["local_path"],
            access_modes=persistent_volume["access_modes"],
            node_affinity=persistent_volume["node_affinity"],
            status_wait=status_wait
        )

        self.client.create_local_pvc(
            name,
            namespace=self.namespace,
            storage_class=self.context["kubernetes"]["storageclass"],
            access_modes=persistent_volume_claim["access_modes"],
            size=persistent_volume_claim["size"]
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
                    "persistentVolumeClaim": {
                        "claimName": name
                    }
                }
            ]
        }

        super(CreateAndDeletePodWithLocalPVVolume, self).run(
            image,
            name=name,
            command=command,
            check_cmd=check_cmd,
            error_regexp=error_regexp,
            volume=volume,
            status_wait=status_wait
        )

        with atomic.ActionTimer(
                self,
                "kubernetes.check_persistent_volume_claim_status"):
            resp = self.client.get_local_pvc(name, namespace=self.namespace)
            self.assertNotEqual("Failed", resp.status.phase)
        with atomic.ActionTimer(self,
                                "kubernetes.check_persistent_volume_status"):
            resp = self.client.get_local_pv(name)
            self.assertNotEqual("Failed", resp.status.phase)

        self.client.delete_local_pvc(
            name,
            namespace=self.namespace,
            status_wait=status_wait
        )

        self.client.delete_local_pv(
            name,
            status_wait=status_wait
        )
