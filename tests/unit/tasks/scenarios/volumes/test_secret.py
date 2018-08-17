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
from xrally_kubernetes.tasks.scenarios.volumes import secret


class CreateAndDeleteSecretVolumeTestCase(test.TestCase):

    def setUp(self):
        super(CreateAndDeleteSecretVolumeTestCase, self).setUp()
        context = {
            "iteration": 1,
            "kubernetes": {
                "namespaces": ["ns"],
                "namespace_choice_method": "round_robin"
            }
        }
        self.scenario = secret.CreateAndDeletePodWithSecretVolume(context)
        self.client = mock.MagicMock()
        self.scenario.client = self.client
        self.scenario.generate_random_name = mock.MagicMock()
        self.scenario.generate_random_name.return_value = "name"

    def test_create_and_delete_success(self):
        self.client.create_pod.return_value = "name"
        self.scenario.run("test/image",
                          command=["ls"],
                          mount_path="/opt/check")

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
                        "secret": {
                            "secretName": "name"
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

    def test_create_failed(self):
        self.client.create_pod.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(rest.ApiException, self.scenario.run, "test/image",
                          mount_path="/opt/check")
        self.assertEqual(0, self.client.delete_pod.call_count)

    def test_delete_failed(self):
        self.client.delete_pod.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(rest.ApiException, self.scenario.run, "test/image",
                          mount_path="/opt/check")
        self.client.create_pod.assert_called_once_with(
            "test/image",
            name="name",
            namespace="ns",
            command=None,
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
                        "secret": {
                            "secretName": "name"
                        }
                    }
                ]
            },
            status_wait=True
        )


class CreateCheckAndDeleteSecretVolumeTestCase(test.TestCase):

    def setUp(self):
        super(CreateCheckAndDeleteSecretVolumeTestCase, self).setUp()
        context = {
            "iteration": 1,
            "kubernetes": {
                "namespaces": ["ns"],
                "namespace_choice_method": "round_robin"
            }
        }
        self.scenario = secret.CreateAndDeletePodWithSecretVolume(context)
        self.client = mock.MagicMock()
        self.scenario.client = self.client
        self.scenario.generate_random_name = mock.MagicMock()
        self.scenario.generate_random_name.return_value = "name"

    def test_create_and_delete_success(self):
        self.client.create_pod.return_value = "name"
        self.scenario.run("test/image", command=["ls"], check_cmd=["ls"],
                          mount_path="/opt/check")

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
                        "secret": {
                            "secretName": "name"
                        }
                    }
                ]
            },
            status_wait=True
        )
        self.client.check_volume_pod.assert_called_once_with(
            "name",
            namespace="ns",
            check_cmd=["ls"],
            error_regexp=None
        )
        self.client.delete_pod.assert_called_once_with(
            "name",
            namespace="ns",
            status_wait=True
        )

    def test_create_failed(self):
        self.client.create_pod.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(rest.ApiException, self.scenario.run, "test/image",
                          mount_path="/opt/check", check_cmd=["ls"])
        self.assertEqual(0, self.client.check_volume_pod.call_count)
        self.assertEqual(0, self.client.delete_pod.call_count)

    def test_delete_failed(self):
        self.client.delete_pod.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(rest.ApiException, self.scenario.run, "test/image",
                          mount_path="/opt/check", check_cmd=["ls"])
        self.client.create_pod.assert_called_once_with(
            "test/image",
            name="name",
            namespace="ns",
            command=None,
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
                        "secret": {
                            "secretName": "name"
                        }
                    }
                ]
            },
            status_wait=True
        )
        self.client.check_volume_pod.assert_called_once()
        self.client.delete_pod.assert_called_once()
