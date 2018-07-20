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

import datetime
import mock
import time

from kubernetes.client import rest

from tests.unit import test
from xrally_kubernetes.tasks.scenarios import pods


class CreateAndDeletePodTestCase(test.TestCase):

    def setUp(self):
        super(CreateAndDeletePodTestCase, self).setUp()
        self.scenario = pods.CreateAndDeletePod()
        self.client = mock.MagicMock()
        self.scenario.client = self.client
        self.scenario.context = {
            "iteration": 1,
            "kubernetes": {
                "namespaces": ["ns"],
                "namespace_choice_method": "round_robin"
            }
        }

    def test_parse_conditions_method(self):
        conditions = []
        time_to_stub = datetime.datetime.now()
        a = mock.MagicMock()
        a.type = "Initialized"
        a.last_transition_time = time_to_stub
        conditions.append(a)
        a = mock.MagicMock()
        a.type = "PodScheduled"
        a.last_transition_time = time_to_stub
        conditions.append(a)
        a = mock.MagicMock()
        a.type = "Ready"
        a.last_transition_time = time_to_stub
        conditions.append(a)

        expected_time = time.mktime(time_to_stub.timetuple())
        actual = self.scenario._parse_pod_status_conditions(conditions)
        self.assertIn({
            'finished_at': expected_time,
            'name': 'kubernetes.scheduled_pod',
            'started_at': expected_time
        }, actual)
        self.assertIn({
            'finished_at': expected_time,
            'name': 'kubernetes.created_pod',
            'started_at': expected_time
        }, actual)
        self.assertIn({
            'finished_at': expected_time,
            'name': 'kubernetes.initialized_pod',
            'started_at': expected_time
        }, actual)

    def test_make_data_from_conditions(self):
        time_to_stub_start = time.mktime(datetime.datetime.now().timetuple())
        time_to_stub_finish = time_to_stub_start + 1
        conditions = [
            {
                'finished_at': time_to_stub_finish,
                'name': 'kubernetes.scheduled_pod',
                'started_at': time_to_stub_start
            },
            {
                'finished_at': time_to_stub_finish,
                'name': 'kubernetes.created_pod',
                'started_at': time_to_stub_start
            },
            {
                'finished_at': time_to_stub_finish,
                'name': 'kubernetes.initialized_pod',
                'started_at': time_to_stub_start
            }
        ]

        expected = [
            ['kubernetes.initialized_pod', 1.0],
            ['kubernetes.scheduled_pod', 1.0],
            ['kubernetes.created_pod', 1.0]
        ]
        self.assertEqual(
            expected,
            self.scenario._make_data_from_conditions(conditions)
        )

    def test_create_and_delete_success(self):
        resp = mock.MagicMock()
        resp.status.conditions = []
        self.client.create_pod.return_value = "test"
        self.client.get_pod.return_value = resp

        self.scenario.run("test/image", command=["ls"])

        self.client.create_pod.assert_called_once_with(
            "test/image",
            namespace="ns",
            command=["ls"],
            status_wait=True
        )
        self.client.get_pod.assert_called_once()
        self.client.delete_pod.assert_called_once_with(
            "test",
            namespace="ns",
            status_wait=True
        )

        self.assertEqual([], self.scenario._output["complete"])
        self.assertEqual([{
            "title": "Pod's conditions total duration",
            "description": "Total durations for pod in each iteration",
            "chart_plugin": "StackedArea",
            "data": [[], [], []],
            "label": "Total seconds",
            "axis_label": "Iteration"
        }], self.scenario._output["additive"])

    def test_create_failed(self):
        self.client.create_pod.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(rest.ApiException, self.scenario.run, "test/image")
        self.assertEqual(0, self.client.get_pod.call_count)
        self.assertEqual(0, self.client.delete_pod.call_count)

    def test_get_pod_failed(self):
        self.client.get_pod.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(rest.ApiException, self.scenario.run, "test/image")
        self.client.create_pod.assert_called_once_with(
            "test/image",
            command=None,
            namespace="ns",
            status_wait=True
        )
        self.assertEqual(0, self.client.delete_pod.call_count)

    def test_delete_pod_failed(self):
        resp = mock.MagicMock()
        resp.status.conditions = []
        self.client.create_pod.return_value = "test"
        self.client.get_pod.return_value = resp
        self.client.delete_pod.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(rest.ApiException, self.scenario.run, "test/image")
        self.client.create_pod.assert_called_once_with(
            "test/image",
            command=None,
            namespace="ns",
            status_wait=True
        )
        self.client.get_pod.assert_called_once_with(
            "test",
            namespace="ns"
        )
