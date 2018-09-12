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
from xrally_kubernetes.tasks.scenarios import jobs


class CreateAndDeleteJobTestCase(test.TestCase):

    def setUp(self):
        super(CreateAndDeleteJobTestCase, self).setUp()
        self.scenario = jobs.CreateAndDeleteJob()
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
        self.client.create_job.return_value = "test"

        self.scenario.run("test/image", ["ls"])

        self.client.create_job.assert_called_once_with(
            namespace="ns",
            image="test/image",
            command=["ls"],
            status_wait=True
        )
        self.client.delete_job.assert_called_once_with(
            "test",
            namespace="ns",
            status_wait=True
        )

    def test_create_failed(self):
        self.client.create_job.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(rest.ApiException, self.scenario.run, "test/image",
                          ["ls"])
        self.client.create_job.assert_called_once_with(
            namespace="ns",
            image="test/image",
            command=["ls"],
            status_wait=True
        )
        self.assertEqual(0, self.client.delete_job.call_count)

    def test_delete_failed(self):
        self.client.create_job.return_value = "test"
        self.client.delete_job.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(rest.ApiException, self.scenario.run, "test/image",
                          ["ls"])
        self.client.create_job.assert_called_once_with(
            command=["ls"],
            namespace="ns",
            image="test/image",
            status_wait=True
        )
