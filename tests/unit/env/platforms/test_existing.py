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


class KubernetesPlatformFromSysEnvTestCase(test.TestCase):

    def test_cert_vars(self):
        sys_env = {
            "KUBERNETES_CERT_AUTH": "stub.crt",
            "KUBERNETES_HOST": "localhost:8443",
            "KUBERNETES_CLIENT_KEY": "client-stub.key",
            "KUBERNETES_CLIENT_CERT": "client-stub.crt"
        }

        def expand_path(x):
            return os.path.abspath(os.path.expanduser(x))

        expected = {
            "server": "localhost:8443",
            "certificate-authority": expand_path("stub.crt"),
            "client-certificate": expand_path("client-stub.crt"),
            "client-key": expand_path("client-stub.key"),
            "tls_insecure": False
        }

        # Test with no tls defined
        res = existing.KubernetesPlatform.create_spec_from_sys_environ(sys_env)
        self.assertTrue(res["available"])
        self.assertEqual(expected, res["spec"])

        # Test with insecure equals False
        sys_env["KUBERNETES_TLS_INSECURE"] = False
        expected["tls_insecure"] = True
        res = existing.KubernetesPlatform.create_spec_from_sys_environ(sys_env)
        self.assertTrue(res["available"])
        self.assertEqual(expected, res["spec"])

        # Test with insecure equals True
        sys_env["KUBERNETES_TLS_INSECURE"] = True
        expected["tls_insecure"] = True
        res = existing.KubernetesPlatform.create_spec_from_sys_environ(sys_env)
        self.assertTrue(res["available"])
        self.assertEqual(expected, res["spec"])

    def test_token_vars(self):
        sys_env = {
            "KUBERNETES_CERT_AUTH": "stub.crt",
            "KUBERNETES_HOST": "localhost:8443",
            "KUBERNETES_API_KEY": "stub api key",
            "KUBERNETES_API_KEY_PREFIX": "Bearer"
        }

        expected = {
            "server": "localhost:8443",
            "certificate-authority": os.path.abspath(
                os.path.expanduser("stub.crt")),
            "api_key": "stub api key",
            "api_key_prefix": "Bearer"
        }

        res = existing.KubernetesPlatform.create_spec_from_sys_environ(sys_env)
        self.assertTrue(res["available"])
        self.assertEqual(expected, res["spec"])

    def test_all_vars(self):
        sys_env = {
            "KUBERNETES_CERT_AUTH": "stub.crt",
            "KUBERNETES_HOST": "localhost:8443",
            "KUBERNETES_API_KEY": "stub api key",
            "KUBERNETES_API_KEY_PREFIX": "Bearer",
            "KUBERNETES_CLIENT_KEY": "client-stub.key",
            "KUBERNETES_CLIENT_CERT": "client-stub.crt",
            "KUBERNETES_TLS_INSECURE": True
        }

        def expand_path(x):
            return os.path.abspath(os.path.expanduser(x))

        expected = {
            "server": "localhost:8443",
            "certificate-authority": expand_path("stub.crt"),
            "client-certificate": expand_path("client-stub.crt"),
            "client-key": expand_path("client-stub.key"),
            "tls_insecure": True
        }

        res = existing.KubernetesPlatform.create_spec_from_sys_environ(sys_env)
        self.assertTrue(res["available"])
        self.assertEqual(expected, res["spec"])

    def test_missing_host_and_cert_auth(self):
        # Test no host and cert_auth
        res = existing.KubernetesPlatform.create_spec_from_sys_environ({})
        self.assertFalse(res["available"])
        self.assertEqual("sys-env has no KUBERNETES_HOST or "
                         "KUBERNETES_CERT_AUTH vars", res["message"])

        # Test no host
        res = existing.KubernetesPlatform.create_spec_from_sys_environ({
            "KUBERNETES_CERT_AUTH": "stub.crt"
        })
        self.assertFalse(res["available"])
        self.assertEqual("sys-env has no KUBERNETES_HOST or "
                         "KUBERNETES_CERT_AUTH vars", res["message"])

        # Test no cert_auth
        res = existing.KubernetesPlatform.create_spec_from_sys_environ({
            "KUBERNETES_HOST": "localhost:8443"
        })
        self.assertFalse(res["available"])
        self.assertEqual("sys-env has no KUBERNETES_HOST or "
                         "KUBERNETES_CERT_AUTH vars", res["message"])

    def test_vars_all_missing(self):
        sys_env = {
            "KUBERNETES_CERT_AUTH": "stub.crt",
            "KUBERNETES_HOST": "localhost:8443"
        }
        res = existing.KubernetesPlatform.create_spec_from_sys_environ(sys_env)
        self.assertFalse(res["available"])
        self.assertEqual("Missing required env variables: "
                         "%(crt)s or %(api)s" % {
                             "crt": ["KUBERNETES_CLIENT_CERT",
                                     "KUBERNETES_CLIENT_KEY",
                                     "KUBERNETES_TLS_INSECURE"],
                             "api": ["KUBERNETES_API_KEY",
                                     "KUBERNETES_API_KEY_PREFIX"]
                         }, res["message"])

    def test_vars_one_missing(self):
        sys_env = {
            "KUBERNETES_CERT_AUTH": "stub.crt",
            "KUBERNETES_HOST": "localhost:8443",
            "KUBERNETES_CLIENT_CERT": "client-stub.crt",
            "KUBERNETES_API_KEY_PREFIX": "Bearer"
        }
        res = existing.KubernetesPlatform.create_spec_from_sys_environ(sys_env)
        self.assertFalse(res["available"])
        self.assertEqual("Missing required env variables: "
                         "%(crt)s or %(api)s" % {
                             "crt": ["KUBERNETES_CLIENT_CERT",
                                     "KUBERNETES_CLIENT_KEY",
                                     "KUBERNETES_TLS_INSECURE"],
                             "api": ["KUBERNETES_API_KEY",
                                     "KUBERNETES_API_KEY_PREFIX"]
                         }, res["message"])
