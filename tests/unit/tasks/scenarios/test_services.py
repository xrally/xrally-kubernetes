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

from tests.unit import test
from xrally_kubernetes.tasks.scenarios import services


class PodWithClusterIPSvcTestCase(test.TestCase):

    def setUp(self):
        super(PodWithClusterIPSvcTestCase, self).setUp()
        self.scenario = services.PodWithClusterIPSvc()
        self.client = mock.MagicMock()
        self.scenario.client = self.client
        self.scenario.context = {
            "iteration": 1,
            "kubernetes": {
                "namespaces": ["ns"],
                "namespace_choice_method": "round_robin"
            }
        }
        self.scenario.generate_random_name = mock.MagicMock()
        self.scenario.generate_random_name.return_value = "testapp"

    def test_create_and_delete_success_no_custom_endpoints(self):
        addr = mock.MagicMock()
        addr.ip = "10.0.0.5"
        port = mock.MagicMock()
        port.port = "3030"
        subset = mock.MagicMock()
        subset.addresses = [addr]
        subset.ports = [port]
        resp = mock.MagicMock()
        resp.subsets = [subset]
        self.client.get_endpoints.return_value = resp
        self.client.create_pod.return_value = "test"

        self.scenario.run(
            "test/image",
            port=80,
            protocol="TCP",
            command=["ls"],
            custom_endpoint=False,
            status_wait=True
        )

        self.client.create_pod.assert_called_once_with(
            image="test/image",
            namespace="ns",
            command=["ls"],
            port=80,
            protocol="TCP",
            labels={"app": "testapp"},
            status_wait=True
        )
        self.client.create_service.assert_called_once_with(
            "test",
            namespace="ns",
            port=80,
            protocol="TCP",
            type="ClusterIP",
            labels={"app": "testapp"}
        )
        self.client.get_endpoints.assert_called_once_with(
            "test",
            namespace="ns"
        )
        self.client.create_job.assert_called_once_with(
            name="test",
            namespace="ns",
            image="appropriate/curl",
            command=["curl", "10.0.0.5:3030"],
            status_wait=True
        )
        self.client.delete_job.assert_called_once_with(
            "test",
            namespace="ns",
            status_wait=True
        )
        self.client.delete_service.assert_called_once_with(
            "test",
            namespace="ns"
        )
        self.client.delete_pod.assert_called_once_with(
            "test",
            namespace="ns",
            status_wait=True
        )

    def test_create_and_delete_success_custom_endpoints(self):
        resp = mock.MagicMock()
        resp.status.pod_ip = "192.168.0.3"
        self.client.get_pod.return_value = resp
        self.client.create_pod.return_value = "test"

        self.scenario.run(
            "test/image",
            port=80,
            protocol="TCP",
            command=["ls"],
            custom_endpoint=True,
            status_wait=True
        )

        self.client.create_pod.assert_called_once_with(
            image="test/image",
            namespace="ns",
            command=["ls"],
            port=80,
            protocol="TCP",
            labels={"app": "testapp"},
            status_wait=True
        )
        self.client.create_service.assert_called_once_with(
            "test",
            namespace="ns",
            port=80,
            protocol="TCP",
            type="ClusterIP",
            labels=None
        )
        self.client.get_pod.assert_called_once_with(
            "test",
            namespace="ns"
        )
        self.client.create_endpoints.assert_called_once_with(
            "test",
            namespace="ns",
            ip="192.168.0.3",
            port=80
        )
        self.client.create_job.assert_called_once_with(
            name="test",
            namespace="ns",
            image="appropriate/curl",
            command=["curl", "192.168.0.3:80"],
            status_wait=True
        )
        self.client.delete_job.assert_called_once_with(
            "test",
            namespace="ns",
            status_wait=True
        )
        self.client.delete_endpoints.assert_called_once_with(
            "test",
            namespace="ns"
        )
        self.client.delete_service.assert_called_once_with(
            "test",
            namespace="ns"
        )
        self.client.delete_pod.assert_called_once_with(
            "test",
            namespace="ns",
            status_wait=True
        )


class PodWithNodePortServiceTestCase(test.TestCase):

    def setUp(self):
        super(PodWithNodePortServiceTestCase, self).setUp()
        self.scenario = services.PodWithNodePortService()
        self.client = mock.MagicMock()
        self.scenario.client = self.client
        self.scenario.context = {
            "iteration": 1,
            "kubernetes": {
                "namespaces": ["ns"],
                "namespace_choice_method": "round_robin"
            },
            "env": {
                "platforms": {
                    "kubernetes": {
                        "server": "https://127.0.0.1:8443"
                    }
                }
            }
        }
        self.scenario.generate_random_name = mock.MagicMock()
        self.scenario.generate_random_name.return_value = "testapp"

    @mock.patch("requests.get")
    def test_create_and_delete_success(self, mock_requests):
        port = mock.MagicMock()
        port.node_port = 30403
        svc = mock.MagicMock()
        svc.spec.ports = [port]
        self.client.get_service.return_value = svc
        self.client.create_pod.return_value = "test"

        self.scenario.run(
            "test/image",
            port=80,
            protocol="TCP",
            command=["ls"],
            status_wait=True
        )

        self.client.create_pod.assert_called_once_with(
            image="test/image",
            namespace="ns",
            command=["ls"],
            port=80,
            protocol="TCP",
            labels={"app": "testapp"},
            status_wait=True
        )
        self.client.create_service.assert_called_once_with(
            "test",
            namespace="ns",
            port=80,
            protocol="TCP",
            type="NodePort",
            labels={"app": "testapp"}
        )
        self.client.get_service.assert_called_once_with(
            "test",
            namespace="ns"
        )
        mock_requests.assert_called_once_with("http://127.0.0.1:30403/")
        self.client.delete_service.assert_called_once_with(
            "test",
            namespace="ns"
        )
        self.client.delete_pod.assert_called_once_with(
            "test",
            namespace="ns",
            status_wait=True
        )
