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
from xrally_kubernetes.tasks.scenarios import daemonsets


class CreateCheckAndDeleteDaemonSetTestCase(test.TestCase):

    def setUp(self):
        super(CreateCheckAndDeleteDaemonSetTestCase, self).setUp()
        self.scenario = daemonsets.CreateCheckAndDeleteDaemonSet()
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
        self.client.create_daemonset.return_value = "test", "testapp"

        self.scenario.run(
            "test/image",
            command=["ls"],
            node_labels=None,
            status_wait=True
        )

        self.client.create_daemonset.assert_called_once_with(
            namespace="ns",
            image="test/image",
            command=["ls"],
            node_labels=None,
            status_wait=True
        )
        self.client.check_daemonset.assert_called_once_with(
            namespace="ns",
            app="testapp",
            node_labels=None
        )
        self.client.delete_daemonset.assert_called_once_with(
            "test",
            namespace="ns",
            status_wait=True
        )

    def test_create_failed(self):
        self.client.create_daemonset.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(rest.ApiException, self.scenario.run, "test/image")
        self.client.create_daemonset.assert_called_once_with(
            namespace="ns",
            image="test/image",
            node_labels=None,
            command=None,
            status_wait=True
        )
        self.assertEqual(0, self.client.check_daemonset.call_count)
        self.assertEqual(0, self.client.delete_daemonset.call_count)

    def test_check_failed(self):
        self.client.create_daemonset.return_value = "test", "testapp"
        self.client.check_daemonset.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(rest.ApiException, self.scenario.run, "test/image")
        self.client.create_daemonset.assert_called_once_with(
            namespace="ns",
            image="test/image",
            node_labels=None,
            command=None,
            status_wait=True
        )
        self.client.check_daemonset.assert_called_once_with(
            namespace="ns",
            app="testapp",
            node_labels=None
        )
        self.assertEqual(0, self.client.delete_daemonset.call_count)

    def test_delete_failed(self):
        self.client.create_daemonset.return_value = "test", "testapp"
        self.client.delete_daemonset.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(rest.ApiException, self.scenario.run, "test/image")
        self.client.create_daemonset.assert_called_once_with(
            command=None,
            namespace="ns",
            node_labels=None,
            image="test/image",
            status_wait=True
        )
        self.client.check_daemonset.assert_called_once()
