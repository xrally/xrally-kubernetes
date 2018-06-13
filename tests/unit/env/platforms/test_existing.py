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

import os

from kubernetes.client import rest
import mock

from tests.unit import test
from xrally_kubernetes.env.platforms import existing


class KubernetesPlatformTestCase(test.TestCase):

    def setUp(self):
        super(KubernetesPlatformTestCase, self).setUp()

        from xrally_kubernetes import service as k8s_service

        p_mock_service = mock.patch.object(k8s_service, "Kubernetes")
        self.service_cls = p_mock_service.start()
        self.service = self.service_cls.return_value
        self.addCleanup(p_mock_service.stop)

    def test_create(self):
        platform = existing.KubernetesPlatform({})
        self.assertEqual(({"tls_insecure": False}, {}), platform.create())

        platform = existing.KubernetesPlatform(
            {
                "certificate-authority": "test",
                "server": "test",
                "client-certificate": "test",
                "client-key": "test",
                "tls_insecure": True
            })
        path_test = os.path.abspath(os.path.expanduser("test"))
        self.assertEqual(({
            "certificate-authority": path_test,
            "server": "test",
            "client-certificate": path_test,
            "client-key": path_test,
            "tls_insecure": True
        }, {}), platform.create())

        platform = existing.KubernetesPlatform(
            {
                "certificate-authority": "test",
                "server": "test",
                "api_key": "test",
                "api_key_prefix": "test"
            })
        path_test = os.path.abspath(os.path.expanduser("test"))
        self.assertEqual(({
            "certificate-authority": path_test,
            "server": "test",
            "api_key": "test",
            "api_key_prefix": "test",
            "tls_insecure": False
        }, {}), platform.create())

    def test_check_health(self):
        self.service_cls.reset_mock()
        self.service.get_version.return_value = 15

        platform = existing.KubernetesPlatform({})
        self.assertEqual({"available": True}, platform.check_health())

    def test_check_health_failed(self):
        self.service_cls.reset_mock()
        self.service.get_version.side_effect = [
            rest.ApiException(status=500, reason="Test")]

        platform = existing.KubernetesPlatform({})
        health = platform.check_health()
        self.assertFalse(health["available"])

        expected_msg = "Something went wrong: (500)\nReason: Test\n"
        self.assertEqual(expected_msg, health["message"])
