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
from rally.common import cfg
from rally import exceptions as rally_exc

from tests.unit import test
from xrally_kubernetes import service

CONF = cfg.CONF


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

        CONF.set_override("status_poll_interval", 0, "kubernetes")
        CONF.set_override("status_total_retries", 1, "kubernetes")
        CONF.set_override("start_prepoll_delay", 0, "kubernetes")

    @property
    def k8s_client(self):
        spec = {
            "api_key_prefix": "stub_prefix",
            "api_key": "stub_key",
            "server": "stub_server",
            "certificate-authority": "stub_auth"
        }
        return service.Kubernetes(spec)

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

    def test_create_namespace(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.k8s_client.create_namespace("test", status_wait=False)

        expected = {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {
                "name": "test",
                "labels": {
                    "role": "test"
                }
            }
        }
        self.client.create_namespace.assert_called_once_with(body=expected)

    def test_create_and_wait_namespace_success(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        read_resp = mock.MagicMock()
        read_resp.status.phase = "Active"
        self.client.read_namespace.return_value = read_resp

        self.k8s_client.create_namespace("test", status_wait=True)

        self.client.create_namespace.assert_called_once()
        self.client.read_namespace.assert_called_once_with("test")

    def test_create_and_wait_namespace_fail_create(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.create_namespace.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.create_namespace,
            "test",
            status_wait=True
        )

        self.client.create_namespace.assert_called_once()
        self.assertEqual(0, self.client.read_namespace.call_count)

    def test_create_and_wait_namespace_fail_read(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.read_namespace.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.create_namespace,
            "test",
            status_wait=True
        )

        self.client.create_namespace.assert_called_once()
        self.client.read_namespace.assert_called_once()

    def test_create_and_wait_namespace_read_timeout(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        CONF.set_override("status_total_retries", 2, "kubernetes")

        read_resp = mock.MagicMock()
        read_resp.status.phase = "Pending"
        self.client.read_namespace.return_value = read_resp

        self.assertRaises(
            rally_exc.TimeoutException,
            self.k8s_client.create_namespace,
            "test",
            status_wait=True
        )

        self.client.create_namespace.assert_called_once()
        self.assertEqual(2, self.client.read_namespace.call_count)

    def test_delete_namespace(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        from kubernetes import client as k8s_config

        self.k8s_client.delete_namespace("test", status_wait=False)

        self.client.delete_namespace.assert_called_once_with(
            body=k8s_config.V1DeleteOptions(),
            name="test"
        )

    def test_delete_namespace_and_wait_termination_success(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.read_namespace.side_effect = [
            rest.ApiException(status=404, reason="Not found")
        ]

        self.k8s_client.delete_namespace("test")

        self.client.delete_namespace.assert_called_once()
        self.client.read_namespace.assert_called_once_with("test")

    def test_delete_namespace_and_wait_termination_delete_failed(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.delete_namespace.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.delete_namespace,
            "test"
        )

        self.client.delete_namespace.assert_called_once()
        self.assertEqual(0, self.client.read_namespace.call_count)

    def test_delete_namespace_and_wait_termination_read_failed(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.read_namespace.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.delete_namespace,
            "test"
        )

        self.client.delete_namespace.assert_called_once()
        self.client.read_namespace.assert_called_once()

    def test_delete_namespace_and_wait_termination_timeout(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        CONF.set_override("status_total_retries", 2, "kubernetes")

        self.assertRaises(
            rally_exc.TimeoutException,
            self.k8s_client.delete_namespace,
            "test"
        )

        self.client.delete_namespace.assert_called_once()
        self.assertEqual(2, self.client.read_namespace.call_count)

    def test_create_spec_from_file(self):
        from kubernetes.config import kube_config
        patcher = mock.patch('os.path.exists')
        mock_thing = patcher.start()
        mock_thing.return_value = True
        kube_config.load_kube_config = mock.MagicMock()
        self.config_cls.reset_mock()

        self.config.host = "stub host"
        self.config.ssl_ca_cert = "stub crt"
        self.config.api_key = {"authorization": "stub"}
        self.config.api_key_prefix = {}
        self.config.cert_file = "client crt"
        self.config.key_file = "client key"
        self.config.verify_ssl = False

        expected = {
            "host": "stub host",
            "certificate-authority": "stub crt",
            "api_key": {"authorization": "stub"},
            "api_key_prefix": {},
            "client-certificate": "client crt",
            "client-key": "client key",
            "tls_insecure": False
        }
        self.assertEqual(expected, service.Kubernetes.create_spec_from_file())
        patcher.stop()

    def test_create_spec_from_file_not_found(self):
        from kubernetes.config import kube_config
        patcher = mock.patch('os.path.exists')
        mock_thing = patcher.start()
        mock_thing.return_value = False
        kube_config.load_kube_config = mock.MagicMock()
        self.config_cls.reset_mock()

        self.assertEqual({}, service.Kubernetes.create_spec_from_file())
        kube_config.load_kube_config.assert_not_called()
        self.config_cls.assert_not_called()
        patcher.stop()

    def test_create_serviceaccount(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        expected = {
            "apiVersion": "v1",
            "kind": "ServiceAccount",
            "metadata": {
                "name": "test"
            }
        }
        self.k8s_client.create_serviceaccount("test", namespace="ns")
        self.client.create_namespaced_service_account.assert_called_once_with(
            body=expected,
            namespace="ns"
        )

    def test_create_secret(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        expected = {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {
                "name": "test",
                "annotations": {
                    "kubernetes.io/service-account.name": "test"
                }
            }
        }
        self.k8s_client.create_secret("test", namespace="ns")
        self.client.create_namespaced_secret.assert_called_once_with(
            body=expected,
            namespace="ns"
        )

    def test_create_pod(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.k8s_client.create_pod(
            "name",
            image="test/image",
            namespace="ns",
            status_wait=False)

        expected = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": "name",
                "labels": {
                    "role": "name"
                }
            },
            "spec": {
                "containers": [
                    {
                        "name": "name",
                        "image": "test/image"
                    }
                ]
            }
        }
        self.client.create_namespaced_pod.assert_called_once_with(
            body=expected,
            namespace="ns"
        )

    def test_create_pod_with_command(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.k8s_client.create_pod(
            "name",
            image="test/image",
            namespace="ns",
            command=["ls"],
            status_wait=False)

        expected = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": "name",
                "labels": {
                    "role": "name"
                }
            },
            "spec": {
                "containers": [
                    {
                        "name": "name",
                        "image": "test/image",
                        "command": ["ls"]
                    }
                ]
            }
        }
        self.client.create_namespaced_pod.assert_called_once_with(
            body=expected,
            namespace="ns"
        )

    def test_create_pod_with_incorrect_command(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.k8s_client.create_pod(
            "name",
            image="test/image",
            namespace="ns",
            command="ls",
            status_wait=False)

        expected = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": "name",
                "labels": {
                    "role": "name"
                }
            },
            "spec": {
                "containers": [
                    {
                        "name": "name",
                        "image": "test/image"
                    }
                ]
            }
        }
        self.client.create_namespaced_pod.assert_called_once_with(
            body=expected,
            namespace="ns"
        )

    def test_create_pod_with_sa(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        client = self.k8s_client
        client._spec["serviceaccounts"] = True
        client.create_pod(
            "name",
            image="test/image",
            namespace="ns",
            status_wait=False)

        expected = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": "name",
                "labels": {
                    "role": "name"
                }
            },
            "spec": {
                "serviceAccountName": "ns",
                "containers": [
                    {
                        "name": "name",
                        "image": "test/image"
                    }
                ]
            }
        }
        self.client.create_namespaced_pod.assert_called_once_with(
            body=expected,
            namespace="ns"
        )

    def test_create_and_wait_pod_success(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        read_resp = mock.MagicMock()
        read_resp.status.phase = "Running"
        self.client.read_namespaced_pod.return_value = read_resp

        self.k8s_client.create_pod(
            "name",
            image="test/image",
            namespace="ns",
            status_wait=True
        )

        self.client.create_namespaced_pod.assert_called_once()
        self.client.read_namespaced_pod.assert_called_once_with(
            "name",
            namespace="ns"
        )

    def test_create_and_wait_pod_fail_create(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.create_namespaced_pod.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.create_pod,
            "name",
            image="test/image",
            namespace="ns",
            status_wait=True
        )

        self.client.create_namespaced_pod.assert_called_once()
        self.assertEqual(0, self.client.read_namespaced_pod.call_count)

    def test_create_and_wait_pod_fail_read(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.read_namespaced_pod.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.create_pod,
            "name",
            image="test/image",
            namespace="ns",
            status_wait=True
        )

        self.client.create_namespaced_pod.assert_called_once()
        self.client.read_namespaced_pod.assert_called_once()

    def test_create_and_wait_pod_read_timeout(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        CONF.set_override("status_total_retries", 2, "kubernetes")

        read_resp = mock.MagicMock()
        read_resp.status.phase = "Pending"
        self.client.read_namespace.return_value = read_resp

        self.assertRaises(
            rally_exc.TimeoutException,
            self.k8s_client.create_pod,
            "name",
            image="test/image",
            namespace="ns",
            status_wait=True
        )

        self.client.create_namespaced_pod.assert_called_once()
        self.assertEqual(2, self.client.read_namespaced_pod.call_count)

    def test_delete_pod(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        from kubernetes import client as k8s_config

        self.k8s_client.delete_pod("test", namespace="ns", status_wait=False)

        self.client.delete_namespaced_pod.assert_called_once_with(
            "test",
            body=k8s_config.V1DeleteOptions(),
            namespace="ns"
        )

    def test_delete_pod_and_wait_termination_success(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.read_namespaced_pod.side_effect = [
            rest.ApiException(status=404, reason="Not found")
        ]

        self.k8s_client.delete_pod("test", namespace="ns")

        self.client.delete_namespaced_pod.assert_called_once()
        self.client.read_namespaced_pod.assert_called_once_with(
            "test", namespace="ns")

    def test_delete_pod_and_wait_termination_delete_failed(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.delete_namespaced_pod.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.delete_pod,
            "test",
            namespace="ns"
        )

        self.client.delete_namespaced_pod.assert_called_once()
        self.assertEqual(0, self.client.read_namespaced_pod.call_count)

    def test_delete_pod_and_wait_termination_read_failed(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.read_namespaced_pod.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.delete_pod,
            "test",
            namespace="ns"
        )

        self.client.delete_namespaced_pod.assert_called_once()
        self.client.read_namespaced_pod.assert_called_once()

    def test_delete_pod_and_wait_termination_timeout(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        CONF.set_override("status_total_retries", 2, "kubernetes")

        self.assertRaises(
            rally_exc.TimeoutException,
            self.k8s_client.delete_pod,
            "test",
            namespace="ns"
        )

        self.client.delete_namespaced_pod.assert_called_once()
        self.assertEqual(2, self.client.read_namespaced_pod.call_count)

    def test_create_pod_with_volume_and_wait_success(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        read_resp = mock.MagicMock()
        read_resp.status.phase = "Running"
        self.client.read_namespaced_pod.return_value = read_resp

        event_resp = mock.MagicMock()
        event_resp.items = []
        self.client.list_namespaced_event.return_value = event_resp

        self.k8s_client.create_pod(
            "name",
            image="test/image",
            namespace="ns",
            volume={
                "mount_path": ["stub"],
                "volume": ["stub"]
            },
            status_wait=True
        )

        self.client.create_namespaced_pod.assert_called_once()
        self.client.read_namespaced_pod.assert_called_once_with(
            "name",
            namespace="ns"
        )
        self.client.list_namespaced_event.assert_called_once_with(
            namespace="ns"
        )

    def test_create_pod_with_volume_and_wait_create_container_error(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        read_resp = mock.MagicMock()
        read_resp.status.phase = "Running"
        self.client.read_namespaced_pod.return_value = read_resp

        event_resp = mock.MagicMock()
        event = mock.MagicMock()
        event.name = "name"
        event.reason = "CreateContainerError"
        event.message = "Test raise"
        event_resp.items = [event]
        self.client.list_namespaced_event.return_value = event_resp

        self.assertRaises(
            rally_exc.RallyException,
            self.k8s_client.create_pod,
            "name",
            image="test/image",
            namespace="ns",
            volume={
                "mount_path": ["stub"],
                "volume": ["stub"]
            },
            status_wait=True
        )

        self.client.create_namespaced_pod.assert_called_once()
        self.assertEqual(0, self.client.read_namespaced_pod.call_count)
        self.client.list_namespaced_event.assert_called_once_with(
            namespace="ns"
        )

    def test_check_volume_pod_success(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        api = mock.MagicMock()
        api.api_client.request = mock.MagicMock()
        self.client.connect_get_namespaced_pod_exec.__self__ = mock.MagicMock()
        self.client.connect_get_namespaced_pod_exec.__self__.return_value = api
        self.client.connect_get_namespaced_pod_exec.return_value = (
            "for success")

        self.assertIsNone(self.k8s_client.check_volume_pod(
            "name",
            namespace="ns",
            check_cmd="check",
            error_regexp="nope"
        ))

    def test_check_volume_pod_exec_failed(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        api = mock.MagicMock()
        api.api_client.request = mock.MagicMock()
        self.client.connect_get_namespaced_pod_exec.__self__ = mock.MagicMock()
        self.client.connect_get_namespaced_pod_exec.__self__.return_value = api
        self.client.connect_get_namespaced_pod_exec.return_value = (
            "exec failed: command not found")

        self.assertRaises(
            rally_exc.RallyException,
            self.k8s_client.check_volume_pod,
            "name",
            namespace="ns",
            check_cmd="check",
            error_regexp="nope"
        )

    def test_check_volume_pod_exec_error_regexp(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        api = mock.MagicMock()
        api.api_client.request = mock.MagicMock()
        self.client.connect_get_namespaced_pod_exec.__self__ = mock.MagicMock()
        self.client.connect_get_namespaced_pod_exec.__self__.return_value = api
        self.client.connect_get_namespaced_pod_exec.return_value = (
            "nope, error response")

        self.assertRaises(
            rally_exc.RallyException,
            self.k8s_client.check_volume_pod,
            "name",
            namespace="ns",
            check_cmd="check",
            error_regexp="nope"
        )

    def test_create_pod_emptydir_volume(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.k8s_client.create_pod(
            "name",
            image="test/image",
            namespace="ns",
            volume={
                "mount_path": [
                    {
                        "name": "stub",
                        "mountPath": "/check"
                    }
                ],
                "volume": [
                    {
                        "name": "stub",
                        "emptyDir": {}
                    }
                ]
            },
            status_wait=False)

        expected = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": "name",
                "labels": {
                    "role": "name"
                }
            },
            "spec": {
                "containers": [
                    {
                        "name": "name",
                        "image": "test/image",
                        "volumeMounts": [
                            {
                                "mountPath": "/check",
                                "name": "stub"
                            }
                        ]
                    }
                ],
                "volumes": [
                    {
                        "name": "stub",
                        "emptyDir": {}
                    }
                ]
            }
        }
        self.client.create_namespaced_pod.assert_called_once_with(
            body=expected,
            namespace="ns"
        )
