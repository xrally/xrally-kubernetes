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

        self._k8s_client = None

    @property
    def k8s_client(self):
        if self._k8s_client is None:
            spec = {
                "api_key_prefix": "stub_prefix",
                "api_key": "stub_key",
                "server": "stub_server",
                "certificate-authority": "stub_auth"
            }
            self._k8s_client = service.Kubernetes(
                spec,
                name_generator=mock.MagicMock()
            )
        return self._k8s_client


class ServiceTestCase(KubernetesServiceTestCase):

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


class NamespacesTestCase(KubernetesServiceTestCase):

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

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "test"
        self.k8s_client.create_namespace(status_wait=False)

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

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "test"
        self.k8s_client.create_namespace(status_wait=True)

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


class PodTestCase(KubernetesServiceTestCase):

    def test_create_pod(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        self.k8s_client.create_pod(
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

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        self.k8s_client.create_pod(
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

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        ex = self.assertRaises(
            ValueError,
            self.k8s_client.create_pod,
            image="test/image",
            namespace="ns",
            command="ls",
            status_wait=False
        )

        self.assertEqual("'command' argument should be list or tuple type, "
                         "found %s" % type("ls"), str(ex))
        self.assertEqual(
            0,
            self.client.create_namespaced_pod.call_count
        )

    def test_create_pod_with_sa(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        client = self.k8s_client
        client._spec["serviceaccounts"] = True
        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        client.create_pod(
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

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        self.k8s_client.create_pod(
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
        self.client.read_namespaced_pod.return_value = read_resp

        self.assertRaises(
            rally_exc.TimeoutException,
            self.k8s_client.create_pod,
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


class ReplicationControllerTestCase(KubernetesServiceTestCase):

    def test_create_replication_controller(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        self.k8s_client.create_rc(
            image="test/image",
            replicas=2,
            namespace="ns",
            status_wait=False)

        expected = {
            "apiVersion": "v1",
            "kind": "ReplicationController",
            "metadata": {
                "name": "name",
            },
            "spec": {
                "replicas": 2,
                "selector": {
                    "app": mock.ANY
                },
                "template": {
                    "metadata": {
                        "name": "name",
                        "labels": {
                            "app": mock.ANY
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
            }
        }
        (self.client.create_namespaced_replication_controller
            .assert_called_once_with(
                body=expected,
                namespace="ns"
            ))

    def test_create_replication_controller_with_command(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        self.k8s_client.create_rc(
            image="test/image",
            replicas=2,
            namespace="ns",
            command=["ls"],
            status_wait=False)

        expected = {
            "apiVersion": "v1",
            "kind": "ReplicationController",
            "metadata": {
                "name": "name",
            },
            "spec": {
                "replicas": 2,
                "selector": {
                    "app": mock.ANY
                },
                "template": {
                    "metadata": {
                        "name": "name",
                        "labels": {
                            "app": mock.ANY
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
            }
        }
        (self.client.create_namespaced_replication_controller
            .assert_called_once_with(
                body=expected,
                namespace="ns"
            ))

    def test_create_replication_controller_with_incorrect_command(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        ex = self.assertRaises(
            ValueError,
            self.k8s_client.create_rc,
            image="test/image",
            replicas=2,
            namespace="ns",
            command="ls",
            status_wait=False
        )

        self.assertEqual("'command' argument should be list or tuple type, "
                         "found %s" % type("ls"), str(ex))
        self.assertEqual(
            0,
            self.client.create_namespaced_replication_controller.call_count
        )

    def test_create_and_wait_replication_controller_success(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        resp = mock.MagicMock()
        resp.status.replicas = 2
        resp.status.ready_replicas = 2
        self.client.read_namespaced_replication_controller.return_value = resp

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        self.k8s_client.create_rc(
            image="test/image",
            namespace="ns",
            replicas=2,
            status_wait=True
        )

        (self.client.create_namespaced_replication_controller
            .assert_called_once())
        (self.client.read_namespaced_replication_controller
            .assert_called_once_with(
                "name",
                namespace="ns"
            ))

    def test_create_and_wait_replication_controller_fail_create(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.create_namespaced_replication_controller.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.create_rc,
            image="test/image",
            namespace="ns",
            replicas=2,
            status_wait=True
        )

        (self.client.create_namespaced_replication_controller
            .assert_called_once())
        self.assertEqual(
            0,
            self.client.read_namespaced_replication_controller.call_count
        )

    def test_create_and_wait_replication_controller_fail_read(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.read_namespaced_replication_controller.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.create_rc,
            image="test/image",
            namespace="ns",
            replicas=2,
            status_wait=True
        )

        (self.client.create_namespaced_replication_controller
            .assert_called_once())
        (self.client.read_namespaced_replication_controller
         .assert_called_once())

    def test_create_and_wait_replication_controller_read_timeout(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        CONF.set_override("status_total_retries", 2, "kubernetes")

        resp = mock.MagicMock()
        resp.status.ready_replicas = None
        self.client.read_namespaced_replication_controller.return_value = resp

        self.assertRaises(
            rally_exc.TimeoutException,
            self.k8s_client.create_rc,
            image="test/image",
            replicas=2,
            namespace="ns",
            status_wait=True
        )

        (self.client.create_namespaced_replication_controller
            .assert_called_once())
        self.assertEqual(
            2,
            self.client.read_namespaced_replication_controller.call_count
        )

    def test_delete_replication_controller(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        from kubernetes import client as k8s_config

        self.k8s_client.delete_rc("test", namespace="ns", status_wait=False)

        (self.client.delete_namespaced_replication_controller
            .assert_called_once_with(
                "test",
                body=k8s_config.V1DeleteOptions(),
                namespace="ns"
            ))

    def test_delete_replication_controller_and_wait_termination_success(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.read_namespaced_replication_controller.side_effect = [
            rest.ApiException(status=404, reason="Not found")
        ]

        self.k8s_client.delete_rc("test", namespace="ns")

        (self.client.delete_namespaced_replication_controller
            .assert_called_once())
        (self.client.read_namespaced_replication_controller
            .assert_called_once_with("test", namespace="ns"))

    def test_delete_replication_controller_delete_failed(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.delete_namespaced_replication_controller.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.delete_rc,
            "test",
            namespace="ns"
        )

        (self.client.delete_namespaced_replication_controller
            .assert_called_once())
        self.assertEqual(
            0,
            self.client.read_namespaced_replication_controller.call_count
        )

    def test_delete_replication_controller_read_failed(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.read_namespaced_replication_controller.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.delete_rc,
            "test",
            namespace="ns"
        )

        (self.client.delete_namespaced_replication_controller
            .assert_called_once())
        (self.client.read_namespaced_replication_controller
            .assert_called_once_with("test", namespace="ns"))

    def test_delete_replication_controller_and_wait_termination_timeout(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        CONF.set_override("status_total_retries", 2, "kubernetes")

        self.assertRaises(
            rally_exc.TimeoutException,
            self.k8s_client.delete_rc,
            "test",
            namespace="ns"
        )

        (self.client.delete_namespaced_replication_controller
            .assert_called_once())
        self.assertEqual(
            2,
            self.client.read_namespaced_replication_controller.call_count
        )


class ReplicaSetServiceTestCase(KubernetesServiceTestCase):

    def setUp(self):
        super(ReplicaSetServiceTestCase, self).setUp()

        from kubernetes.client.apis import extensions_v1beta1_api

        p_mock_client = mock.patch.object(extensions_v1beta1_api,
                                          "ExtensionsV1beta1Api")
        self.client_cls = p_mock_client.start()
        self.client = self.client_cls.return_value
        self.addCleanup(p_mock_client.stop)

    def test_create_replicaset(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        self.k8s_client.create_replicaset(
            image="test/image",
            replicas=2,
            namespace="ns",
            status_wait=False)

        expected = {
            "apiVersion": "extensions/v1beta1",
            "kind": "ReplicaSet",
            "metadata": {
                "name": "name",
                "labels": {
                    "app": mock.ANY
                }
            },
            "spec": {
                "replicas": 2,
                "selector": {
                    "matchLabels": {
                        "app": mock.ANY
                    }
                },
                "template": {
                    "metadata": {
                        "name": "name",
                        "labels": {
                            "app": mock.ANY
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
            }
        }
        (self.client.create_namespaced_replica_set
            .assert_called_once_with(
                body=expected,
                namespace="ns"
            ))

    def test_create_replicaset_with_command(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        self.k8s_client.create_replicaset(
            image="test/image",
            replicas=2,
            namespace="ns",
            command=["ls"],
            status_wait=False)

        expected = {
            "apiVersion": "extensions/v1beta1",
            "kind": "ReplicaSet",
            "metadata": {
                "name": "name",
                "labels": {
                    "app": mock.ANY
                }
            },
            "spec": {
                "replicas": 2,
                "selector": {
                    "matchLabels": {
                        "app": mock.ANY
                    }
                },
                "template": {
                    "metadata": {
                        "name": "name",
                        "labels": {
                            "app": mock.ANY
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
            }
        }
        (self.client.create_namespaced_replica_set
            .assert_called_once_with(
                body=expected,
                namespace="ns"
            ))

    def test_create_replicaset_with_incorrect_command(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        ex = self.assertRaises(
            ValueError,
            self.k8s_client.create_replicaset,
            image="test/image",
            replicas=2,
            namespace="ns",
            command="ls",
            status_wait=False
        )

        self.assertEqual("'command' argument should be list or tuple type, "
                         "found %s" % type("ls"), str(ex))
        self.assertEqual(
            0,
            self.client.create_namespaced_replica_set.call_count
        )

    def test_create_and_wait_replicaset_success(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        resp = mock.MagicMock()
        resp.status.replicas = 2
        resp.status.ready_replicas = 2
        self.client.read_namespaced_replica_set.return_value = resp

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        self.k8s_client.create_replicaset(
            image="test/image",
            namespace="ns",
            replicas=2,
            status_wait=True
        )

        (self.client.create_namespaced_replica_set
            .assert_called_once())
        (self.client.read_namespaced_replica_set
            .assert_called_once_with(
                "name",
                namespace="ns"
            ))

    def test_create_and_wait_replicaset_fail_create(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.create_namespaced_replica_set.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.create_replicaset,
            image="test/image",
            namespace="ns",
            replicas=2,
            status_wait=True
        )

        (self.client.create_namespaced_replica_set
            .assert_called_once())
        self.assertEqual(
            0,
            self.client.read_namespaced_replica_set.call_count
        )

    def test_create_and_wait_replicaset_fail_read(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.read_namespaced_replica_set.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.create_replicaset,
            image="test/image",
            namespace="ns",
            replicas=2,
            status_wait=True
        )

        (self.client.create_namespaced_replica_set
            .assert_called_once())
        (self.client.read_namespaced_replica_set
         .assert_called_once())

    def test_create_and_wait_replicaset_read_timeout(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        CONF.set_override("status_total_retries", 2, "kubernetes")

        resp = mock.MagicMock()
        resp.status.ready_replicas = None
        self.client.read_namespaced_replica_set.return_value = resp

        self.assertRaises(
            rally_exc.TimeoutException,
            self.k8s_client.create_replicaset,
            image="test/image",
            replicas=2,
            namespace="ns",
            status_wait=True
        )

        (self.client.create_namespaced_replica_set
            .assert_called_once())
        self.assertEqual(
            2,
            self.client.read_namespaced_replica_set.call_count
        )

    def test_delete_replicaset(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        from kubernetes import client as k8s_config

        self.k8s_client.delete_replicaset("test", namespace="ns",
                                          status_wait=False)

        (self.client.delete_namespaced_replica_set
            .assert_called_once_with(
                "test",
                body=k8s_config.V1DeleteOptions(),
                namespace="ns"
            ))

    def test_delete_replicaset_and_wait_termination_success(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.read_namespaced_replica_set.side_effect = [
            rest.ApiException(status=404, reason="Not found")
        ]

        self.k8s_client.delete_replicaset("test", namespace="ns")

        (self.client.delete_namespaced_replica_set
            .assert_called_once())
        (self.client.read_namespaced_replica_set
            .assert_called_once_with("test", namespace="ns"))

    def test_delete_replicaset_delete_failed(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.delete_namespaced_replica_set.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.delete_replicaset,
            "test",
            namespace="ns"
        )

        (self.client.delete_namespaced_replica_set
            .assert_called_once())
        self.assertEqual(
            0,
            self.client.read_namespaced_replica_set.call_count
        )

    def test_delete_replicaset_read_failed(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.read_namespaced_replica_set.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.delete_replicaset,
            "test",
            namespace="ns"
        )

        (self.client.delete_namespaced_replica_set
            .assert_called_once())
        (self.client.read_namespaced_replica_set
            .assert_called_once_with("test", namespace="ns"))

    def test_delete_replicaset_and_wait_termination_timeout(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        CONF.set_override("status_total_retries", 2, "kubernetes")

        self.assertRaises(
            rally_exc.TimeoutException,
            self.k8s_client.delete_replicaset,
            "test",
            namespace="ns"
        )

        (self.client.delete_namespaced_replica_set
            .assert_called_once())
        self.assertEqual(
            2,
            self.client.read_namespaced_replica_set.call_count
        )


class PodWithVolumeTestCase(KubernetesServiceTestCase):

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

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        self.k8s_client.create_pod(
            image="test/image",
            namespace="ns",
            volume={
                "mount_path": ["stub"],
                "volume": ["stub"]
            },
            name=None,
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

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        self.k8s_client.create_pod(
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

    def test_create_pod_secret_volume(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        self.k8s_client.create_pod(
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
                        "secret": {
                            "secretName": "stub"
                        }
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
                        "secret": {
                            "secretName": "stub"
                        }
                    }
                ]
            }
        }
        self.client.create_namespaced_pod.assert_called_once_with(
            body=expected,
            namespace="ns"
        )

    def test_create_pod_hostpath_volume(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        self.k8s_client.create_pod(
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
                        "hostPath": {
                            "type": "Directory",
                            "path": "/path"
                        }
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
                        "hostPath": {
                            "type": "Directory",
                            "path": "/path"
                        }
                    }
                ]
            }
        }
        self.client.create_namespaced_pod.assert_called_once_with(
            body=expected,
            namespace="ns"
        )

    def test_create_pod_configmap_volume(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"

        self.k8s_client.create_pod(
            image="test/image",
            namespace="ns",
            volume={
                "mount_path": [
                    {
                        "name": "stub",
                        "mountPath": "/check.txt",
                        "subPath": "check.txt"
                    }
                ],
                "volume": [
                    {
                        "name": "stub",
                        "configMap": {
                            "name": "stub"
                        }
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
                                "mountPath": "/check.txt",
                                "name": "stub",
                                "subPath": "check.txt"
                            }
                        ]
                    }
                ],
                "volumes": [
                    {
                        "name": "stub",
                        "configMap": {
                            "name": "stub"
                        }
                    }
                ]
            }
        }
        self.client.create_namespaced_pod.assert_called_once_with(
            body=expected,
            namespace="ns"
        )


class DeploymentServiceTestCase(KubernetesServiceTestCase):

    def setUp(self):
        super(DeploymentServiceTestCase, self).setUp()

        from kubernetes.client.apis import extensions_v1beta1_api

        p_mock_client = mock.patch.object(extensions_v1beta1_api,
                                          "ExtensionsV1beta1Api")
        self.client_cls = p_mock_client.start()
        self.client = self.client_cls.return_value
        self.addCleanup(p_mock_client.stop)

    def test_create_deployment(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        self.k8s_client.create_deployment(
            image="test/image",
            replicas=2,
            namespace="ns",
            status_wait=False)

        expected = {
            "apiVersion": "extensions/v1beta1",
            "kind": "Deployment",
            "metadata": {
                "name": "name",
                "labels": {
                    "app": mock.ANY
                }
            },
            "spec": {
                "replicas": 2,
                "template": {
                    "metadata": {
                        "name": "name",
                        "labels": {
                            "app": mock.ANY
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
            }
        }
        (self.client.create_namespaced_deployment
            .assert_called_once_with(
                body=expected,
                namespace="ns"
            ))

    def test_create_deployment_with_command(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        self.k8s_client.create_deployment(
            image="test/image",
            replicas=2,
            namespace="ns",
            command=["ls"],
            status_wait=False)

        expected = {
            "apiVersion": "extensions/v1beta1",
            "kind": "Deployment",
            "metadata": {
                "name": "name",
                "labels": {
                    "app": mock.ANY
                }
            },
            "spec": {
                "replicas": 2,
                "template": {
                    "metadata": {
                        "name": "name",
                        "labels": {
                            "app": mock.ANY
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
            }
        }
        (self.client.create_namespaced_deployment
            .assert_called_once_with(
                body=expected,
                namespace="ns"
            ))

    def test_create_deployment_with_incorrect_command(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        ex = self.assertRaises(
            ValueError,
            self.k8s_client.create_deployment,
            image="test/image",
            replicas=2,
            namespace="ns",
            command="ls",
            status_wait=False
        )

        self.assertEqual("'command' argument should be list or tuple type, "
                         "found %s" % type("ls"), str(ex))
        self.assertEqual(
            0,
            self.client.create_namespaced_deployment.call_count
        )

    def test_create_deployment_with_incorrect_env(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        ex = self.assertRaises(
            ValueError,
            self.k8s_client.create_deployment,
            image="test/image",
            replicas=2,
            namespace="ns",
            command=["ls"],
            env="VAR",
            status_wait=False
        )

        self.assertEqual("'env' argument should be list or tuple type, "
                         "found %s" % type("VAR"), str(ex))
        self.assertEqual(
            0,
            self.client.create_namespaced_deployment.call_count
        )

    def test_create_deployment_with_incorrect_resources(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        ex = self.assertRaises(
            ValueError,
            self.k8s_client.create_deployment,
            image="test/image",
            replicas=2,
            namespace="ns",
            command=["ls"],
            resources=("limit", "unlimited"),
            status_wait=False
        )

        self.assertEqual("'resources' argument should be dict type, found "
                         "%s" % type(("limit", "unlimited")), str(ex))
        self.assertEqual(
            0,
            self.client.create_namespaced_deployment.call_count
        )

    def test_create_and_wait_deployment_success(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        resp = mock.MagicMock()
        resp.status.replicas = 2
        resp.status.ready_replicas = 2
        self.client.read_namespaced_deployment_status.return_value = resp

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        self.k8s_client.create_deployment(
            image="test/image",
            namespace="ns",
            replicas=2,
            status_wait=True
        )

        (self.client.create_namespaced_deployment
            .assert_called_once())
        (self.client.read_namespaced_deployment_status
            .assert_called_once_with(
                name="name",
                namespace="ns"
            ))

    def test_create_and_wait_deployment_fail_create(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.create_namespaced_deployment.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.create_deployment,
            image="test/image",
            namespace="ns",
            replicas=2,
            status_wait=True
        )

        (self.client.create_namespaced_deployment
            .assert_called_once())
        self.assertEqual(
            0,
            self.client.read_namespaced_deployment_status.call_count
        )

    def test_create_and_wait_deployment_fail_read(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.read_namespaced_deployment_status.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.create_deployment,
            image="test/image",
            namespace="ns",
            replicas=2,
            status_wait=True
        )

        (self.client.create_namespaced_deployment
            .assert_called_once())
        (self.client.read_namespaced_deployment_status
         .assert_called_once())

    def test_create_and_wait_deployment_read_timeout(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        CONF.set_override("status_total_retries", 2, "kubernetes")

        resp = mock.MagicMock()
        resp.status.ready_replicas = None
        self.client.read_namespaced_deployment_status.return_value = resp

        self.assertRaises(
            rally_exc.TimeoutException,
            self.k8s_client.create_deployment,
            image="test/image",
            replicas=2,
            namespace="ns",
            status_wait=True
        )

        (self.client.create_namespaced_deployment
            .assert_called_once())
        self.assertEqual(
            2,
            self.client.read_namespaced_deployment_status.call_count
        )

    def test_delete_deployment(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        from kubernetes import client as k8s_config

        self.k8s_client.delete_deployment("test", namespace="ns",
                                          status_wait=False)

        (self.client.delete_namespaced_deployment
            .assert_called_once_with(
                name="test",
                body=k8s_config.V1DeleteOptions(),
                namespace="ns"
            ))

    def test_delete_deployment_and_wait_termination_success(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.read_namespaced_deployment_status.side_effect = [
            rest.ApiException(status=404, reason="Not found")
        ]

        self.k8s_client.delete_deployment("test", namespace="ns")

        (self.client.delete_namespaced_deployment
            .assert_called_once())
        (self.client.read_namespaced_deployment_status
            .assert_called_once_with(name="test", namespace="ns"))

    def test_delete_deployment_delete_failed(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.delete_namespaced_deployment.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.delete_deployment,
            "test",
            namespace="ns"
        )

        (self.client.delete_namespaced_deployment
            .assert_called_once())
        self.assertEqual(
            0,
            self.client.read_namespaced_deployment_status.call_count
        )

    def test_delete_deployment_read_failed(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.read_namespaced_deployment_status.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.delete_deployment,
            "test",
            namespace="ns"
        )

        (self.client.delete_namespaced_deployment
            .assert_called_once())
        (self.client.read_namespaced_deployment_status
            .assert_called_once_with(name="test", namespace="ns"))

    def test_delete_deployment_and_wait_termination_timeout(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        CONF.set_override("status_total_retries", 2, "kubernetes")

        self.assertRaises(
            rally_exc.TimeoutException,
            self.k8s_client.delete_deployment,
            "test",
            namespace="ns"
        )

        (self.client.delete_namespaced_deployment
            .assert_called_once())
        self.assertEqual(
            2,
            self.client.read_namespaced_deployment_status.call_count
        )


class JobServiceTestCase(KubernetesServiceTestCase):

    def setUp(self):
        super(JobServiceTestCase, self).setUp()

        from kubernetes.client.apis import batch_v1_api

        p_mock_client = mock.patch.object(batch_v1_api, "BatchV1Api")
        self.client_cls = p_mock_client.start()
        self.client = self.client_cls.return_value
        self.addCleanup(p_mock_client.stop)

    def test_create_job(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        self.k8s_client.create_job(
            image="test/image",
            command=["ls"],
            namespace="ns",
            status_wait=False)

        expected = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "name": "name"
            },
            "spec": {
                "template": {
                    "metadata": {
                        "name": "name"
                    },
                    "spec": {
                        "restartPolicy": "Never",
                        "containers": [
                            {
                                "name": "name",
                                "image": "test/image",
                                "command": ["ls"]
                            }
                        ]
                    }
                }
            }
        }
        self.client.create_namespaced_job.assert_called_once_with(
            body=expected,
            namespace="ns"
        )

    def test_create_and_wait_job_success(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        resp = mock.MagicMock()
        resp.status.succeeded = 1
        self.client.read_namespaced_job.return_value = resp

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        self.k8s_client.create_job(
            image="test/image",
            namespace="ns",
            command=["ls"],
            status_wait=True
        )

        self.client.create_namespaced_job.assert_called_once()
        self.client.read_namespaced_job.assert_called_once_with(
            "name",
            namespace="ns"
        )

    def test_create_and_wait_job_fail_create(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.create_namespaced_job.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.create_job,
            image="test/image",
            namespace="ns",
            command=["ls"],
            status_wait=True
        )

        self.client.create_namespaced_job.assert_called_once()
        self.assertEqual(0, self.client.read_namespaced_job.call_count)

    def test_create_and_wait_job_fail_read(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.read_namespaced_job.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.create_job,
            image="test/image",
            namespace="ns",
            command=["ls"],
            status_wait=True
        )

        self.client.create_namespaced_job.assert_called_once()
        self.client.read_namespaced_job.assert_called_once()

    def test_create_and_wait_job_read_timeout(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        CONF.set_override("status_total_retries", 2, "kubernetes")

        resp = mock.MagicMock()
        resp.status.succeeded = 0
        self.client.read_namespaced_job.return_value = resp

        self.assertRaises(
            rally_exc.TimeoutException,
            self.k8s_client.create_job,
            image="test/image",
            command=["ls"],
            namespace="ns",
            status_wait=True
        )

        self.client.create_namespaced_job.assert_called_once()
        self.assertEqual(2, self.client.read_namespaced_job.call_count)

    def test_delete_job(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        from kubernetes import client as k8s_config

        self.k8s_client.delete_job("test", namespace="ns", status_wait=False)

        self.client.delete_namespaced_job.assert_called_once_with(
            "test",
            body=k8s_config.V1DeleteOptions(),
            namespace="ns"
        )

    def test_delete_job_and_wait_termination_success(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.read_namespaced_job.side_effect = [
            rest.ApiException(status=404, reason="Not found")
        ]

        self.k8s_client.delete_job("test", namespace="ns")

        self.client.delete_namespaced_job.assert_called_once()
        self.client.read_namespaced_job.assert_called_once_with(
            "test",
            namespace="ns"
        )

    def test_delete_job_delete_failed(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.delete_namespaced_job.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.delete_job,
            "test",
            namespace="ns"
        )

        self.client.delete_namespaced_job.assert_called_once()
        self.assertEqual(0, self.client.read_namespaced_job.call_count)

    def test_delete_job_read_failed(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.read_namespaced_job.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.delete_job,
            "test",
            namespace="ns"
        )

        self.client.delete_namespaced_job.assert_called_once()
        self.client.read_namespaced_job.assert_called_once_with(
            "test",
            namespace="ns"
        )

    def test_delete_job_and_wait_termination_timeout(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        CONF.set_override("status_total_retries", 2, "kubernetes")

        self.assertRaises(
            rally_exc.TimeoutException,
            self.k8s_client.delete_job,
            "test",
            namespace="ns"
        )

        self.client.delete_namespaced_job.assert_called_once()
        self.assertEqual(2, self.client.read_namespaced_job.call_count)


class StatefulSetServiceTestCase(KubernetesServiceTestCase):

    def setUp(self):
        super(StatefulSetServiceTestCase, self).setUp()

        from kubernetes.client.apis import apps_v1_api

        p_mock_client = mock.patch.object(apps_v1_api, "AppsV1Api")
        self.client_cls = p_mock_client.start()
        self.client = self.client_cls.return_value
        self.addCleanup(p_mock_client.stop)

    def test_create_statefulset(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        self.k8s_client.create_statefulset(
            image="test/image",
            replicas=2,
            namespace="ns",
            status_wait=False)

        expected = {
            "apiVersion": "apps/v1",
            "kind": "StatefulSet",
            "metadata": {
                "name": "name",
                "labels": {
                    "app": mock.ANY
                }
            },
            "spec": {
                "selector": {
                    "matchLabels": {
                        "app": mock.ANY
                    }
                },
                "replicas": 2,
                "template": {
                    "metadata": {
                        "name": "name",
                        "labels": {
                            "app": mock.ANY
                        }
                    },
                    "spec": {
                        "containers": [
                            {
                                "image": "test/image",
                                "name": "name"
                            }
                        ]
                    }
                }
            }
        }
        (self.client.create_namespaced_stateful_set
            .assert_called_once_with(
                body=expected,
                namespace="ns"
            ))

    def test_create_statefulset_with_command(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        self.k8s_client.create_statefulset(
            image="test/image",
            replicas=2,
            namespace="ns",
            command=["ls"],
            status_wait=False)

        expected = {
            "apiVersion": "apps/v1",
            "kind": "StatefulSet",
            "metadata": {
                "name": "name",
                "labels": {
                    "app": mock.ANY
                }
            },
            "spec": {
                "selector": {
                    "matchLabels": {
                        "app": mock.ANY
                    }
                },
                "replicas": 2,
                "template": {
                    "metadata": {
                        "name": "name",
                        "labels": {
                            "app": mock.ANY
                        }
                    },
                    "spec": {
                        "containers": [
                            {
                                "image": "test/image",
                                "name": "name",
                                "command": ["ls"]
                            }
                        ]
                    }
                }
            }
        }
        (self.client.create_namespaced_stateful_set
            .assert_called_once_with(
                body=expected,
                namespace="ns"
            ))

    def test_create_statefulset_with_incorrect_command(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        ex = self.assertRaises(
            ValueError,
            self.k8s_client.create_statefulset,
            image="test/image",
            replicas=2,
            namespace="ns",
            command="ls",
            status_wait=False
        )

        self.assertEqual("'command' argument should be list or tuple type, "
                         "found %s" % type("ls"), str(ex))
        self.assertEqual(
            0,
            self.client.create_namespaced_stateful_set.call_count
        )

    def test_create_and_wait_statefulset_success(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        resp = mock.MagicMock()
        resp.status.replicas = 2
        resp.status.ready_replicas = 2
        self.client.read_namespaced_stateful_set.return_value = resp

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        self.k8s_client.create_statefulset(
            image="test/image",
            namespace="ns",
            replicas=2,
            status_wait=True
        )

        (self.client.create_namespaced_stateful_set
            .assert_called_once())
        (self.client.read_namespaced_stateful_set
            .assert_called_once_with(
                "name",
                namespace="ns"
            ))

    def test_create_and_wait_statefulset_fail_create(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.create_namespaced_stateful_set.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.create_statefulset,
            image="test/image",
            namespace="ns",
            replicas=2,
            status_wait=True
        )

        (self.client.create_namespaced_stateful_set
            .assert_called_once())
        self.assertEqual(
            0,
            self.client.read_namespaced_stateful_set.call_count
        )

    def test_create_and_wait_statefulset_fail_read(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.read_namespaced_stateful_set.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.create_statefulset,
            image="test/image",
            namespace="ns",
            replicas=2,
            status_wait=True
        )

        (self.client.create_namespaced_stateful_set
            .assert_called_once())
        (self.client.read_namespaced_stateful_set
         .assert_called_once())

    def test_create_and_wait_statefulset_read_timeout(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        CONF.set_override("status_total_retries", 2, "kubernetes")

        resp = mock.MagicMock()
        resp.status.ready_replicas = None
        self.client.read_namespaced_stateful_set.return_value = resp

        self.assertRaises(
            rally_exc.TimeoutException,
            self.k8s_client.create_statefulset,
            image="test/image",
            replicas=2,
            namespace="ns",
            status_wait=True
        )

        (self.client.create_namespaced_stateful_set
            .assert_called_once())
        self.assertEqual(
            2,
            self.client.read_namespaced_stateful_set.call_count
        )

    def test_delete_statefulset(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        from kubernetes import client as k8s_config

        self.k8s_client.delete_statefulset("test", namespace="ns",
                                           status_wait=False)

        (self.client.delete_namespaced_stateful_set
            .assert_called_once_with(
                "test",
                body=k8s_config.V1DeleteOptions(),
                namespace="ns"
            ))

    def test_delete_statefulset_and_wait_termination_success(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.read_namespaced_stateful_set.side_effect = [
            rest.ApiException(status=404, reason="Not found")
        ]

        self.k8s_client.delete_statefulset("test", namespace="ns")

        (self.client.delete_namespaced_stateful_set
            .assert_called_once())
        (self.client.read_namespaced_stateful_set
            .assert_called_once_with("test", namespace="ns"))

    def test_delete_statefulset_delete_failed(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.delete_namespaced_stateful_set.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.delete_statefulset,
            "test",
            namespace="ns"
        )

        (self.client.delete_namespaced_stateful_set
            .assert_called_once())
        self.assertEqual(
            0,
            self.client.read_namespaced_stateful_set.call_count
        )

    def test_delete_statefulset_read_failed(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.read_namespaced_stateful_set.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.delete_statefulset,
            "test",
            namespace="ns"
        )

        (self.client.delete_namespaced_stateful_set
            .assert_called_once())
        (self.client.read_namespaced_stateful_set
            .assert_called_once_with("test", namespace="ns"))

    def test_delete_statefulset_and_wait_termination_timeout(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        CONF.set_override("status_total_retries", 2, "kubernetes")

        self.assertRaises(
            rally_exc.TimeoutException,
            self.k8s_client.delete_statefulset,
            "test",
            namespace="ns"
        )

        (self.client.delete_namespaced_stateful_set
            .assert_called_once())
        self.assertEqual(
            2,
            self.client.read_namespaced_stateful_set.call_count
        )


class KubernetesServicesServiceTestCase(KubernetesServiceTestCase):

    def test_create_service_success(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        expected = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": "name",
                "labels": {
                    "check-label": "true"
                }
            },
            "spec": {
                "type": "ClusterIP",
                "ports": [
                    {
                        "port": 80,
                        "protocol": "TCP"
                    }
                ],
                "selector": {
                    "check-label": "true"
                }
            }
        }

        self.k8s_client.create_service(
            "name",
            namespace="ns",
            port=80,
            protocol="TCP",
            type="ClusterIP",
            labels={"check-label": "true"}
        )

        self.client.create_namespaced_service.assert_called_once_with(
            body=expected,
            namespace="ns"
        )

    def test_create_service_fail(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.create_namespaced_service.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.create_service,
            "name",
            namespace="ns",
            port=80,
            protocol="TCP",
            type="ClusterIP",
            labels={"check-label": "true"}
        )

    def test_get_service_success(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()
        self.k8s_client.get_service("name", namespace="ns")
        self.client.read_namespaced_service.assert_called_once()

    def test_get_service_fail(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.read_namespaced_service.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.get_service,
            "name",
            namespace="ns"
        )

    def test_delete_service_success(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()
        self.k8s_client.delete_service("name", namespace="ns")
        self.client.delete_namespaced_service.assert_called_once_with(
            "name",
            namespace="ns",
            body=mock.ANY
        )

    def test_delete_service_failed(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.delete_namespaced_service.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.delete_service,
            "name",
            namespace="ns"
        )

    def test_create_get_and_endpoints(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        expected = {
            "apiVersion": "v1",
            "kind": "Endpoints",
            "metadata": {
                "name": "name"
            },
            "subsets": [
                {
                    "addresses": [
                        {
                            "ip": "10.0.0.3"
                        }
                    ],
                    "ports": [
                        {
                            "port": "30433"
                        }
                    ]
                }
            ]
        }

        self.k8s_client.create_endpoints(
            "name",
            namespace="ns",
            ip="10.0.0.3",
            port="30433"
        )
        self.client.create_namespaced_endpoints.assert_called_once_with(
            body=expected,
            namespace="ns"
        )

        self.k8s_client.get_endpoints("name", namespace="ns")
        self.client.read_namespaced_endpoints.assert_called_once()

        self.k8s_client.delete_endpoints("name", namespace="ns")
        self.client.delete_namespaced_endpoints.assert_called_once_with(
            "name",
            namespace="ns",
            body=mock.ANY
        )


class PodWithLocalPVVolumeTestCase(KubernetesServiceTestCase):

    def test_create_local_pv_no_wait(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        self.k8s_client.create_local_pv(
            None,
            storage_class="local",
            size="1Gi",
            volume_mode="stubMode",
            local_path="/check",
            access_modes=["ReadWriteOnly"],
            node_affinity={"stub": "double stub"},
            status_wait=False
        )

        expected = {
            "kind": "PersistentVolume",
            "apiVersion": "v1",
            "metadata": {
                "name": "name"
            },
            "spec": {
                "capacity": {
                    "storage": "1Gi"
                },
                "volumeMode": "stubMode",
                "accessModes": ["ReadWriteOnly"],
                "persistentVolumeReclaimPolicy": "Retain",
                "storageClassName": "local",
                "local": {
                    "path": "/check"
                },
                "nodeAffinity": {
                    "stub": "double stub"
                }
            }
        }

        self.client.create_persistent_volume.assert_called_once_with(
            body=expected)

    def test_create_local_pv_wait_for_status(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        read_resp = mock.MagicMock()
        read_resp.status.phase = "Available"
        self.client.read_persistent_volume.return_value = read_resp
        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        self.k8s_client.create_local_pv(
            None,
            storage_class="local",
            size="1Gi",
            volume_mode="stubMode",
            local_path="/check",
            access_modes=["ReadWriteOnly"],
            node_affinity={"stub": "double stub"},
            status_wait=True
        )

        self.client.create_persistent_volume.assert_called_once()
        self.client.read_persistent_volume.assert_called_once()

    def test_create_local_pv_wait_for_status_error(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.read_persistent_volume.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]
        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        self.assertRaises(
            rest.ApiException,
            self.k8s_client.create_local_pv,
            None,
            storage_class="local",
            size="1Gi",
            volume_mode="stubMode",
            local_path="/check",
            access_modes=["ReadWriteOnly"],
            node_affinity={"stub": "double stub"},
            status_wait=True
        )

        self.client.create_persistent_volume.assert_called_once()

    def test_create_local_pvc(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.k8s_client.create_local_pvc(
            "name",
            namespace="ns",
            storage_class="local",
            access_modes=["ReadWriteOnly"],
            size="1Gi"
        )

        expected = {
            "kind": "PersistentVolumeClaim",
            "apiVersion": "v1",
            "metadata": {
                "name": "name"
            },
            "spec": {
                "resources": {
                    "requests": {
                        "storage": "1Gi"
                    }
                },
                "accessModes": ["ReadWriteOnly"],
                "storageClassName": "local"
            }
        }

        self.client.create_namespaced_persistent_volume_claim(
            namespace="ns",
            body=expected
        )

    def test_create_pod_local_pv_volume(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        self.k8s_client.create_pod(
            image="test/image",
            namespace="ns",
            volume={
                "mount_path": [
                    {
                        "mountPath": "/check",
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
                                "name": "name"
                            }
                        ]
                    }
                ],
                "volumes": [
                    {
                        "name": "name",
                        "persistentVolumeClaim": {
                            "claimName": "name"
                        }
                    }
                ]
            }
        }
        self.client.create_namespaced_pod.assert_called_once_with(
            body=expected,
            namespace="ns"
        )


class DaemonSetServiceTestCase(KubernetesServiceTestCase):

    def setUp(self):
        super(DaemonSetServiceTestCase, self).setUp()

        from kubernetes.client.apis import core_v1_api
        from kubernetes.client.apis import extensions_v1beta1_api

        p_mock_client = mock.patch.object(extensions_v1beta1_api,
                                          "ExtensionsV1beta1Api")
        self.client_cls = p_mock_client.start()
        self.client = self.client_cls.return_value
        self.addCleanup(p_mock_client.stop)

        p_mock_client_v1 = mock.patch.object(core_v1_api, "CoreV1Api")
        self.client_v1_cls = p_mock_client_v1.start()
        self.client_v1 = self.client_v1_cls.return_value
        self.addCleanup(p_mock_client_v1.stop)

    def test_create_daemonset(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        self.k8s_client.create_daemonset(
            image="test/image",
            namespace="ns",
            node_labels=None,
            status_wait=False)

        expected = {
            "apiVersion": "extensions/v1beta1",
            "kind": "DaemonSet",
            "metadata": {
                "name": "name"
            },
            "spec": {
                "template": {
                    "metadata": {
                        "name": "name",
                        "labels": {
                            "app": mock.ANY
                        }
                    },
                    "spec": {
                        "containers": [
                            {
                                "image": "test/image",
                                "name": "name"
                            }
                        ]
                    }
                }
            }
        }
        (self.client.create_namespaced_daemon_set
            .assert_called_once_with(
                body=expected,
                namespace="ns"
            ))

    def test_create_daemonset_with_command(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        self.k8s_client.create_daemonset(
            image="test/image",
            namespace="ns",
            command=["ls"],
            node_labels=None,
            status_wait=False)

        expected = {
            "apiVersion": "extensions/v1beta1",
            "kind": "DaemonSet",
            "metadata": {
                "name": "name"
            },
            "spec": {
                "template": {
                    "metadata": {
                        "name": "name",
                        "labels": {
                            "app": mock.ANY
                        }
                    },
                    "spec": {
                        "containers": [
                            {
                                "image": "test/image",
                                "name": "name",
                                "command": ["ls"]
                            }
                        ]
                    }
                }
            }
        }
        (self.client.create_namespaced_daemon_set
            .assert_called_once_with(
                body=expected,
                namespace="ns"
            ))

    def test_create_daemonset_with_incorrect_command(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        ex = self.assertRaises(
            ValueError,
            self.k8s_client.create_daemonset,
            image="test/image",
            namespace="ns",
            command="ls",
            node_labels=None,
            status_wait=False
        )
        self.assertEqual("'command' argument should be list or tuple type, "
                         "found %s" % type("ls"), str(ex))
        self.assertEqual(
            0,
            self.client.create_namespaced_daemon_set.call_count
        )

    def test_create_and_wait_daemonset_success_node_no_filter(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()
        self.client_v1_cls.reset_mock()

        resp = mock.MagicMock()
        resp.status.number_ready = 1
        self.client.read_namespaced_daemon_set.return_value = resp

        node = mock.MagicMock()
        node.metadata.name = "n"
        nodes = mock.MagicMock()
        nodes.items = [node]
        self.client_v1.list_node.return_value = nodes

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        self.k8s_client.create_daemonset(
            image="test/image",
            namespace="ns",
            node_labels=None,
            status_wait=True
        )

        self.client.create_namespaced_daemon_set.assert_called_once()
        self.client.read_namespaced_daemon_set.assert_called_once_with(
            "name",
            namespace="ns"
        )
        self.client_v1.list_node.assert_called_once()

    def test_create_and_wait_daemonset_success_node_filtered(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()
        self.client_v1_cls.reset_mock()

        resp = mock.MagicMock()
        resp.status.number_ready = 1
        self.client.read_namespaced_daemon_set.return_value = resp

        node1 = mock.MagicMock()
        node1.metadata.name = "n"
        node1.metadata.labels = {
            "test/node": "true"
        }
        node2 = mock.MagicMock()
        node2.metadata.name = "n3"
        node2.metadata.labels = {
            "test/node": "false"
        }
        nodes = mock.MagicMock()
        nodes.items = [node1, node2]
        self.client_v1.list_node.return_value = nodes

        self.k8s_client.generate_random_name = mock.MagicMock()
        self.k8s_client.generate_random_name.return_value = "name"
        self.k8s_client.create_daemonset(
            image="test/image",
            namespace="ns",
            node_labels={"test/node": "true"},
            status_wait=True
        )

        self.client.create_namespaced_daemon_set.assert_called_once()
        self.client.read_namespaced_daemon_set.assert_called_once_with(
            "name",
            namespace="ns"
        )
        self.client_v1.list_node.assert_called_once()

    def test_create_and_wait_daemonset_fail_create(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.create_namespaced_daemon_set.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.create_daemonset,
            image="test/image",
            namespace="ns",
            node_labels=None,
            status_wait=True
        )

        (self.client.create_namespaced_daemon_set
            .assert_called_once())
        self.assertEqual(0, self.client.read_namespaced_daemon_set.call_count)

    def test_create_and_wait_daemonset_fail_read(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.read_namespaced_daemon_set.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.create_daemonset,
            image="test/image",
            namespace="ns",
            node_labels=None,
            status_wait=True
        )

        self.client.create_namespaced_daemon_set.assert_called_once()
        self.client.read_namespaced_daemon_set.assert_called_once()
        self.assertEqual(0, self.client_v1.list_node.call_count)

    def test_delete_daemonset(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        from kubernetes import client as k8s_config

        self.k8s_client.delete_daemonset("test", namespace="ns",
                                         status_wait=False)

        self.client.delete_namespaced_daemon_set.assert_called_once_with(
            "test",
            body=k8s_config.V1DeleteOptions(),
            namespace="ns"
        )

    def test_delete_daemonset_and_wait_termination_success(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.read_namespaced_daemon_set.side_effect = [
            rest.ApiException(status=404, reason="Not found")
        ]

        self.k8s_client.delete_daemonset("test", namespace="ns")

        self.client.delete_namespaced_daemon_set.assert_called_once()
        self.client.read_namespaced_daemon_set.assert_called_once_with(
            "test",
            namespace="ns"
        )

    def test_delete_daemonset_delete_failed(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.delete_namespaced_daemon_set.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.delete_daemonset,
            "test",
            namespace="ns"
        )

        self.client.delete_namespaced_daemon_set.assert_called_once()
        self.assertEqual(0, self.client.read_namespaced_daemon_set.call_count)

    def test_delete_daemonset_read_failed(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        self.client.read_namespaced_daemon_set.side_effect = [
            rest.ApiException(status=500, reason="Test")
        ]

        self.assertRaises(
            rest.ApiException,
            self.k8s_client.delete_daemonset,
            "test",
            namespace="ns"
        )

        self.client.delete_namespaced_daemon_set.assert_called_once()
        self.client.read_namespaced_daemon_set.assert_called_once_with(
            "test",
            namespace="ns"
        )

    def test_delete_daemonset_and_wait_termination_timeout(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()

        CONF.set_override("status_total_retries", 2, "kubernetes")

        self.assertRaises(
            rally_exc.TimeoutException,
            self.k8s_client.delete_daemonset,
            "test",
            namespace="ns"
        )

        self.client.delete_namespaced_daemon_set.assert_called_once()
        self.assertEqual(2, self.client.read_namespaced_daemon_set.call_count)

    def test_check_daemonsets_success(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()
        self.client_v1_cls.reset_mock()

        node1 = mock.MagicMock()
        node1.metadata.name = "n"
        node1.metadata.labels = {
            "test/node": "true"
        }
        node2 = mock.MagicMock()
        node2.metadata.name = "n3"
        node2.metadata.labels = {
            "test/node": "false"
        }
        nodes = mock.MagicMock()
        nodes.items = [node1, node2]
        self.client_v1.list_node.return_value = nodes

        pod = mock.MagicMock()
        pod.spec.node_name = "n"
        pods = mock.MagicMock()
        pods.items = [pod]
        self.client_v1.list_namespaced_pod.return_value = pods

        self.k8s_client.check_daemonset(
            "ns",
            app="testapp",
            node_labels={"test/node": "true"}
        )

        self.client_v1.list_namespaced_pod.assert_called_once_with(
            namespace="ns",
            label_selector="app=testapp"
        )
        self.client_v1.list_node.assert_called_once()

    def test_check_daemonsets_fail(self):
        self.config_cls.reset_mock()
        self.api_cls.reset_mock()
        self.client_cls.reset_mock()
        self.client_v1_cls.reset_mock()

        node1 = mock.MagicMock()
        node1.metadata.name = "n"
        node1.metadata.labels = {
            "test/node": "true"
        }
        node2 = mock.MagicMock()
        node2.metadata.name = "n2"
        node2.metadata.labels = {
            "test/node": "true"
        }
        node3 = mock.MagicMock()
        node3.metadata.name = "n3"
        node3.metadata.labels = {
            "test/node": "false"
        }
        nodes = mock.MagicMock()
        nodes.items = [node1, node2, node3]
        self.client_v1.list_node.return_value = nodes

        pod = mock.MagicMock()
        pod.spec.node_name = "n"
        pods = mock.MagicMock()
        pods.items = [pod]
        self.client_v1.list_namespaced_pod.return_value = pods

        self.assertRaises(
            rally_exc.RallyException,
            self.k8s_client.check_daemonset,
            "ns",
            app="testapp",
            node_labels={"test/node": "true"}
        )

        self.client_v1.list_namespaced_pod.assert_called_once_with(
            namespace="ns",
            label_selector="app=testapp"
        )
        self.client_v1.list_node.assert_called_once()
