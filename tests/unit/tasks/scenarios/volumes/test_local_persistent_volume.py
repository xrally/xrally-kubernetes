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

import mock

from kubernetes.client import rest

from tests.unit import test
from xrally_kubernetes.tasks.scenarios.volumes import local_persistent_volume


class CreateAndDeleteLocalPVVolumeTestCase(test.TestCase):

    def setUp(self):
        super(CreateAndDeleteLocalPVVolumeTestCase, self).setUp()
        context = {
            "iteration": 1,
            "kubernetes": {
                "namespaces": ["ns"],
                "namespace_choice_method": "round_robin",
                "storageclass": "local"
            }
        }
        self.scenario = (
            local_persistent_volume.CreateAndDeletePodWithLocalPVVolume(
                context
            )
        )
        self.client = mock.MagicMock()
        self.scenario.client = self.client
        self.scenario.generate_random_name = mock.MagicMock()
        self.scenario.generate_random_name.return_value = "name"

    def test_create_and_delete_success(self):
        self.client.create_pod.return_value = "name"
        self.scenario.run(
            "test/image",
            command=["ls"],
            mount_path="/opt/check",
            persistent_volume={
                "size": "1Gi",
                "volume_mode": "Block",
                "local_path": "/check",
                "access_modes": ["ReadWriteOnly"],
                "node_affinity": {"stub": "stub"}
            },
            persistent_volume_claim={
                "size": "1Gi",
                "access_modes": ["ReadWriteOnly"]
            },
            status_wait=True
        )

        self.client.create_local_pv.assert_called_once_with(
            "name",
            storage_class="local",
            size="1Gi",
            volume_mode="Block",
            local_path="/check",
            access_modes=["ReadWriteOnly"],
            node_affinity={"stub": "stub"},
            status_wait=True
        )
        self.client.create_local_pvc(
            "name",
            namespace="ns",
            storage_class="local",
            access_modes=["ReadWriteOnly"],
            size="1Gi"
        )
        self.client.create_pod.assert_called_once_with(
            "test/image",
            name="name",
            namespace="ns",
            command=["ls"],
            volume={
                "mount_path": [
                    {
                        "mountPath": "/opt/check",
                        "name": "name"
                    }
                ],
                "volume": [
                    {
                        "name": "name",
                        "persistentVolumeClaim": {
                            "claimName": "name"
                        }
                    }
                ]
            },
            status_wait=True
        )
        self.assertEqual(0, self.client.check_volume_pod.call_count)
        self.client.delete_pod.assert_called_once_with(
            "name",
            namespace="ns",
            status_wait=True
        )
        self.client.get_local_pvc.assert_called_once()
        self.client.get_local_pv.assert_called_once()
        self.client.delete_local_pvc.assert_called_once_with(
            "name",
            namespace="ns",
            status_wait=True
        )
        self.client.delete_local_pv.assert_called_once_with(
            "name",
            status_wait=True
        )

    def test_create_pv_failed(self):
        kwargs = dict(
            image="test/image",
            command=["ls"],
            mount_path="/opt/check",
            persistent_volume={
                "size": "1Gi",
                "volume_mode": "Block",
                "local_path": "/check",
                "access_modes": ["ReadWriteOnly"],
                "node_affinity": {"stub": "stub"}
            },
            persistent_volume_claim={
                "size": "1Gi",
                "access_modes": ["ReadWriteOnly"]
            },
            status_wait=True
        )

        self.client.create_local_pv.side_effect = [
            rest.ApiException(status=500, reason="Test")]
        self.assertRaises(rest.ApiException, self.scenario.run, **kwargs)

    def test_create_pvc_failed(self):
        kwargs = dict(
            image="test/image",
            command=["ls"],
            mount_path="/opt/check",
            persistent_volume={
                "size": "1Gi",
                "volume_mode": "Block",
                "local_path": "/check",
                "access_modes": ["ReadWriteOnly"],
                "node_affinity": {"stub": "stub"}
            },
            persistent_volume_claim={
                "size": "1Gi",
                "access_modes": ["ReadWriteOnly"]
            },
            status_wait=True
        )
        self.client.create_local_pvc.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]
        self.assertRaises(rest.ApiException, self.scenario.run, **kwargs)

    def test_create_pod_failed(self):
        kwargs = dict(
            image="test/image",
            command=["ls"],
            mount_path="/opt/check",
            persistent_volume={
                "size": "1Gi",
                "volume_mode": "Block",
                "local_path": "/check",
                "access_modes": ["ReadWriteOnly"],
                "node_affinity": {"stub": "stub"}
            },
            persistent_volume_claim={
                "size": "1Gi",
                "access_modes": ["ReadWriteOnly"]
            },
            status_wait=True
        )
        self.client.create_pod.side_effect = [
            rest.ApiException(status=500, reason="Test")]
        self.assertRaises(rest.ApiException, self.scenario.run, **kwargs)

    def test_delete_failed_pod(self):
        kwargs = dict(
            image="test/image",
            command=["ls"],
            mount_path="/opt/check",
            persistent_volume={
                "size": "1Gi",
                "volume_mode": "Block",
                "local_path": "/check",
                "access_modes": ["ReadWriteOnly"],
                "node_affinity": {"stub": "stub"}
            },
            persistent_volume_claim={
                "size": "1Gi",
                "access_modes": ["ReadWriteOnly"]
            },
            status_wait=True
        )
        self.client.delete_pod.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]
        self.assertRaises(rest.ApiException, self.scenario.run, **kwargs)

    def test_delete_failed_pvc(self):
        kwargs = dict(
            image="test/image",
            command=["ls"],
            mount_path="/opt/check",
            persistent_volume={
                "size": "1Gi",
                "volume_mode": "Block",
                "local_path": "/check",
                "access_modes": ["ReadWriteOnly"],
                "node_affinity": {"stub": "stub"}
            },
            persistent_volume_claim={
                "size": "1Gi",
                "access_modes": ["ReadWriteOnly"]
            },
            status_wait=True
        )
        self.client.delete_local_pvc.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]
        self.assertRaises(rest.ApiException, self.scenario.run, **kwargs)

    def test_delete_failed_pv(self):
        kwargs = dict(
            image="test/image",
            command=["ls"],
            mount_path="/opt/check",
            persistent_volume={
                "size": "1Gi",
                "volume_mode": "Block",
                "local_path": "/check",
                "access_modes": ["ReadWriteOnly"],
                "node_affinity": {"stub": "stub"}
            },
            persistent_volume_claim={
                "size": "1Gi",
                "access_modes": ["ReadWriteOnly"]
            },
            status_wait=True
        )
        self.client.delete_local_pv.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]
        self.assertRaises(rest.ApiException, self.scenario.run, **kwargs)


class CreateCheckAndDeleteLocalPVVolumeTestCase(test.TestCase):

    def setUp(self):
        super(CreateCheckAndDeleteLocalPVVolumeTestCase, self).setUp()
        context = {
            "iteration": 1,
            "kubernetes": {
                "namespaces": ["ns"],
                "namespace_choice_method": "round_robin",
                "storageclass": "local"
            }
        }
        self.scenario = (
            local_persistent_volume.CreateAndDeletePodWithLocalPVVolume(
                context
            )
        )
        self.client = mock.MagicMock()
        self.scenario.client = self.client
        self.scenario.generate_random_name = mock.MagicMock()
        self.scenario.generate_random_name.return_value = "name"

    def test_create_and_delete_success(self):
        self.client.create_pod.return_value = "name"
        self.scenario.run(
            "test/image",
            command=["ls"],
            mount_path="/opt/check",
            persistent_volume={
                "size": "1Gi",
                "volume_mode": "Block",
                "local_path": "/check",
                "access_modes": ["ReadWriteOnly"],
                "node_affinity": {"stub": "stub"}
            },
            persistent_volume_claim={
                "size": "1Gi",
                "access_modes": ["ReadWriteOnly"]
            },
            check_cmd=["ls", "/opt/check"],
            error_regexp="No such file",
            status_wait=True
        )

        self.client.create_local_pv.assert_called_once_with(
            "name",
            storage_class="local",
            size="1Gi",
            volume_mode="Block",
            local_path="/check",
            access_modes=["ReadWriteOnly"],
            node_affinity={"stub": "stub"},
            status_wait=True
        )
        self.client.create_local_pvc(
            "name",
            namespace="ns",
            storage_class="local",
            access_modes=["ReadWriteOnly"],
            size="1Gi"
        )
        self.client.create_pod.assert_called_once_with(
            "test/image",
            name="name",
            namespace="ns",
            command=["ls"],
            volume={
                "mount_path": [
                    {
                        "mountPath": "/opt/check",
                        "name": "name"
                    }
                ],
                "volume": [
                    {
                        "name": "name",
                        "persistentVolumeClaim": {
                            "claimName": "name"
                        }
                    }
                ]
            },
            status_wait=True
        )
        self.client.check_volume_pod.assert_called_once_with(
            "name",
            namespace="ns",
            check_cmd=["ls", "/opt/check"],
            error_regexp="No such file"
        )
        self.client.delete_pod.assert_called_once_with(
            "name",
            namespace="ns",
            status_wait=True
        )
        self.client.get_local_pvc.assert_called_once()
        self.client.get_local_pv.assert_called_once()
        self.client.delete_local_pvc.assert_called_once_with(
            "name",
            namespace="ns",
            status_wait=True
        )
        self.client.delete_local_pv.assert_called_once_with(
            "name",
            status_wait=True
        )

    def test_create_pv_failed(self):
        kwargs = dict(
            image="test/image",
            command=["ls"],
            mount_path="/opt/check",
            persistent_volume={
                "size": "1Gi",
                "volume_mode": "Block",
                "local_path": "/check",
                "access_modes": ["ReadWriteOnly"],
                "node_affinity": {"stub": "stub"}
            },
            persistent_volume_claim={
                "size": "1Gi",
                "access_modes": ["ReadWriteOnly"]
            },
            check_cmd=["ls"],
            status_wait=True
        )

        self.client.create_local_pv.side_effect = [
            rest.ApiException(status=500, reason="Test")]
        self.assertRaises(rest.ApiException, self.scenario.run, **kwargs)
        self.assertEqual(0, self.client.check_volume_pod.call_count)
        self.assertEqual(0, self.client.delete_pod.call_count)

    def test_create_pvc_failed(self):
        kwargs = dict(
            image="test/image",
            command=["ls"],
            mount_path="/opt/check",
            persistent_volume={
                "size": "1Gi",
                "volume_mode": "Block",
                "local_path": "/check",
                "access_modes": ["ReadWriteOnly"],
                "node_affinity": {"stub": "stub"}
            },
            persistent_volume_claim={
                "size": "1Gi",
                "access_modes": ["ReadWriteOnly"]
            },
            check_cmd=["ls"],
            status_wait=True
        )
        self.client.create_local_pvc.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]
        self.assertRaises(rest.ApiException, self.scenario.run, **kwargs)
        self.assertEqual(0, self.client.check_volume_pod.call_count)
        self.assertEqual(0, self.client.delete_pod.call_count)

    def test_create_pod_failed(self):
        kwargs = dict(
            image="test/image",
            command=["ls"],
            mount_path="/opt/check",
            persistent_volume={
                "size": "1Gi",
                "volume_mode": "Block",
                "local_path": "/check",
                "access_modes": ["ReadWriteOnly"],
                "node_affinity": {"stub": "stub"}
            },
            persistent_volume_claim={
                "size": "1Gi",
                "access_modes": ["ReadWriteOnly"]
            },
            check_cmd=["ls"],
            status_wait=True
        )
        self.client.create_pod.side_effect = [
            rest.ApiException(status=500, reason="Test")]
        self.assertRaises(rest.ApiException, self.scenario.run, **kwargs)
        self.assertEqual(0, self.client.check_volume_pod.call_count)
        self.assertEqual(0, self.client.delete_pod.call_count)

    def test_delete_failed_pod(self):
        kwargs = dict(
            image="test/image",
            command=["ls"],
            mount_path="/opt/check",
            persistent_volume={
                "size": "1Gi",
                "volume_mode": "Block",
                "local_path": "/check",
                "access_modes": ["ReadWriteOnly"],
                "node_affinity": {"stub": "stub"}
            },
            persistent_volume_claim={
                "size": "1Gi",
                "access_modes": ["ReadWriteOnly"]
            },
            check_cmd=["ls"],
            status_wait=True
        )
        self.client.delete_pod.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]
        self.assertRaises(rest.ApiException, self.scenario.run, **kwargs)
        self.client.check_volume_pod.assert_called_once()

    def test_delete_failed_pvc(self):
        kwargs = dict(
            image="test/image",
            command=["ls"],
            mount_path="/opt/check",
            persistent_volume={
                "size": "1Gi",
                "volume_mode": "Block",
                "local_path": "/check",
                "access_modes": ["ReadWriteOnly"],
                "node_affinity": {"stub": "stub"}
            },
            persistent_volume_claim={
                "size": "1Gi",
                "access_modes": ["ReadWriteOnly"]
            },
            check_cmd=["ls"],
            status_wait=True
        )
        self.client.delete_local_pvc.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]
        self.assertRaises(rest.ApiException, self.scenario.run, **kwargs)
        self.client.check_volume_pod.assert_called_once()

    def test_delete_failed_pv(self):
        kwargs = dict(
            image="test/image",
            command=["ls"],
            mount_path="/opt/check",
            persistent_volume={
                "size": "1Gi",
                "volume_mode": "Block",
                "local_path": "/check",
                "access_modes": ["ReadWriteOnly"],
                "node_affinity": {"stub": "stub"}
            },
            persistent_volume_claim={
                "size": "1Gi",
                "access_modes": ["ReadWriteOnly"]
            },
            check_cmd=["ls"],
            status_wait=True
        )
        self.client.delete_local_pv.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]
        self.assertRaises(rest.ApiException, self.scenario.run, **kwargs)
        self.client.check_volume_pod.assert_called_once()
