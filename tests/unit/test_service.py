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
from xrally_kubernetes import service


class KubernetesServiceTestCase(test.TestCase):

    def setUp(self):
        super(KubernetesServiceTestCase, self).setUp()
        from kubernetes import client as k8s_config
        from kubernetes.client import api_client
        from kubernetes.client.apis import core_v1_api

        if hasattr(k8s_config, "ConfigurationObject"):
            p_mock_config = mock.patch.object(k8s_config,
                                              "ConfigurationObject")
        else:
            p_mock_config = mock.patch.object(k8s_config, "Configuration")
        self.config_cls = p_mock_config.start()
        self.config = self.config_cls.return_value
        self.addCleanup(p_mock_config.stop)

        p_mock_api = mock.patch.object(api_client, "ApiClient")
        self.api_cls = p_mock_api.start()
        self.api = self.api_cls.return_value
        self.addCleanup(p_mock_api.stop)

        p_mock_client = mock.patch.object(core_v1_api, "CoreV1Api")
        self.client_cls = p_mock_client.start()
        self.client = self.client_cls.return_value
        self.addCleanup(p_mock_client.stop)

    def test__init__kubernetes_version(self):
        from kubernetes import client as k8s_config

        spec = {
            "client-certificate": "stub_cert",
            "client-key": "stub_key",
            "server": "stub_server",
            "certificate-authority": "stub_auth"
        }

        k8s_service = service.Kubernetes(spec)

        self.config_cls.assert_called_once()
        if hasattr(k8s_config, "ConfigurationObject"):
            self.assertEqual(3, k8s_service._k8s_client_version)
        else:
            self.assertEqual(4, k8s_service._k8s_client_version)

    def test___init___cert_without_tls(self):
        # setUp method called it
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        spec = {
            "client-certificate": "stub_cert",
            "client-key": "stub_key",
            "server": "stub_server",
            "certificate-authority": "stub_auth"
        }

        service.Kubernetes(spec)

        self.config_cls.assert_called_once()
        self.api_cls.assert_called_once()
        self.client_cls.assert_called_once()
        eq_vals = {
            "host": "stub_server",
            "cert_file": "stub_cert",
            "key_file": "stub_key",
            "ssl_ca_cert": "stub_auth"
        }
        for key, value in eq_vals.items():
            self.assertEqual(value, getattr(self.config, key))

    def test___init___cert_with_tls(self):
        # setUp method called it
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        spec = {
            "client-certificate": "stub_cert",
            "client-key": "stub_key",
            "server": "stub_server",
            "certificate-authority": "stub_auth",
            "tls_insecure": True
        }

        service.Kubernetes(spec)

        self.config_cls.assert_called_once()
        self.api_cls.assert_called_once()
        self.client_cls.assert_called_once()
        eq_vals = {
            "host": "stub_server",
            "cert_file": "stub_cert",
            "key_file": "stub_key",
            "ssl_ca_cert": "stub_auth",
            "verify_ssl": False
        }
        for key, value in eq_vals.items():
            self.assertEqual(value, getattr(self.config, key))

    def test___init___api(self):
        # setUp method called it
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        spec = {
            "api_key_prefix": "stub_prefix",
            "api_key": "stub_key",
            "server": "stub_server",
            "certificate-authority": "stub_auth"
        }

        service.Kubernetes(spec)

        self.config_cls.assert_called_once()
        self.api_cls.assert_called_once()
        self.client_cls.assert_called_once()
        eq_vals = {
            "host": "stub_server",
            "api_key_prefix": {"authorization": "stub_prefix"},
            "api_key": {"authorization": "stub_key"},
            "ssl_ca_cert": "stub_auth"
        }
        for key, value in eq_vals.items():
            self.assertEqual(value, getattr(self.config, key))

    def test_list_namespaces(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        spec = {
            "api_key_prefix": "stub_prefix",
            "api_key": "stub_key",
            "server": "stub_server",
            "certificate-authority": "stub_auth"
        }
        k8s_client = service.Kubernetes(spec)

        items = []
        expected = []
        for i in range(3):
            item = mock.MagicMock()
            item.metadata.name = i
            item.metadata.uid = i
            item.metadata.labels = {"test": "test-%s" % i}
            items.append(item)
            expected.append({"name": i,
                             "uid": i,
                             "labels": {"test": "test-%s" % i}})
        resp = mock.MagicMock()
        resp.items = items
        self.client.list_namespace = mock.MagicMock()
        self.client.list_namespace.return_value = resp

        list_ns = k8s_client.list_namespaces()

        self.assertEqual(expected, list_ns)
