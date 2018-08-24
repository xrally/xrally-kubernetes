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
from xrally_kubernetes.tasks.scenarios import statefulsets


class CreateAndDeleteStatefulSetTestCase(test.TestCase):

    def setUp(self):
        super(CreateAndDeleteStatefulSetTestCase, self).setUp()
        self.scenario = statefulsets.CreateAndDeleteStatefulSet()
        self.client = mock.MagicMock()
        self.scenario.client = self.client
        self.scenario.context = {
            "iteration": 1,
            "kubernetes": {
                "namespaces": ["ns"],
                "namespace_choice_method": "round_robin"
            }
        }

    def test_create_and_delete_success(self):
        self.client.create_statefulset.return_value = "test"

        self.scenario.run("test/image", 2, command=["ls"])

        self.client.create_statefulset.assert_called_once_with(
            namespace="ns",
            image="test/image",
            replicas=2,
            command=["ls"],
            status_wait=True
        )
        self.client.delete_statefulset.assert_called_once_with(
            "test",
            namespace="ns",
            status_wait=True
        )

    def test_create_failed(self):
        self.client.create_statefulset.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(rest.ApiException, self.scenario.run,
                          "test/image", 2)
        self.client.create_statefulset.assert_called_once_with(
            namespace="ns",
            image="test/image",
            replicas=2,
            command=None,
            status_wait=True
        )
        self.assertEqual(0, self.client.delete_statefulset.call_count)

    def test_delete_failed(self):
        self.client.create_statefulset.return_value = "test"
        self.client.delete_statefulset.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(rest.ApiException, self.scenario.run,
                          "test/image", 2)
        self.client.create_statefulset.assert_called_once_with(
            command=None,
            namespace="ns",
            replicas=2,
            image="test/image",
            status_wait=True
        )


class CreateScaleAndDeleteStatefulSetTestCase(test.TestCase):

    def setUp(self):
        super(CreateScaleAndDeleteStatefulSetTestCase, self).setUp()
        self.scenario = statefulsets.CreateScaleAndDeleteStatefulSet()
        self.client = mock.MagicMock()
        self.scenario.client = self.client
        self.scenario.context = {
            "iteration": 1,
            "kubernetes": {
                "namespaces": ["ns"],
                "namespace_choice_method": "round_robin"
            }
        }

    def test_create_and_delete_success(self):
        self.client.create_statefulset.return_value = "test"

        self.scenario.run("test/image", 2, 3, command=["ls"])

        self.client.create_statefulset.assert_called_once_with(
            namespace="ns",
            image="test/image",
            replicas=2,
            command=["ls"],
            status_wait=True
        )
        self.assertEqual(2, self.client.scale_statefulset.call_count)
        self.client.delete_statefulset.assert_called_once_with(
            name="test",
            namespace="ns",
            status_wait=True
        )

    def test_create_failed(self):
        self.client.create_statefulset.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(rest.ApiException, self.scenario.run,
                          "test/image", 2, 3)
        self.client.create_statefulset.assert_called_once_with(
            namespace="ns",
            image="test/image",
            replicas=2,
            command=None,
            status_wait=True
        )
        self.assertEqual(0, self.client.scale_statefulset.call_count)
        self.assertEqual(0, self.client.delete_statefulset.call_count)

    def test_first_scale_failed(self):
        self.client.create_statefulset.return_value = "test"
        self.client.scale_statefulset.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(rest.ApiException, self.scenario.run,
                          "test/image", 2, 3)
        self.client.create_statefulset.assert_called_once_with(
            namespace="ns",
            image="test/image",
            replicas=2,
            command=None,
            status_wait=True
        )
        self.client.scale_statefulset.assert_called_once_with(
            "test",
            namespace="ns",
            replicas=3,
            status_wait=True
        )
        self.assertEqual(0, self.client.delete_statefulset.call_count)

    def test_second_scale_failed(self):
        self.client.create_statefulset.return_value = "test"
        self.client.scale_statefulset.side_effect = [
            None, rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(rest.ApiException, self.scenario.run,
                          "test/image", 2, 3)
        self.client.create_statefulset.assert_called_once_with(
            namespace="ns",
            image="test/image",
            replicas=2,
            command=None,
            status_wait=True
        )
        self.assertEqual(2, self.client.scale_statefulset.call_count)
        self.assertEqual(dict(
            namespace="ns",
            replicas=2,
            status_wait=True
        ), self.client.scale_statefulset.call_args[1])
        self.assertEqual(0, self.client.delete_statefulset.call_count)

    def test_delete_failed(self):
        self.client.create_statefulset.return_value = "test"
        self.client.delete_statefulset.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(rest.ApiException, self.scenario.run,
                          "test/image", 2, 3)
        self.client.create_statefulset.assert_called_once_with(
            command=None,
            namespace="ns",
            replicas=2,
            image="test/image",
            status_wait=True
        )
        self.assertEqual(2, self.client.scale_statefulset.call_count)
