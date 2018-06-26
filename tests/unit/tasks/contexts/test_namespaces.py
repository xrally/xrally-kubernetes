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

import copy
import mock

from tests.unit import test
from xrally_kubernetes.tasks.contexts import namespaces


class NamespacesContextTestCase(test.TestCase):

    def setUp(self):
        super(NamespacesContextTestCase, self).setUp()

        from xrally_kubernetes import service as k8s_service

        p_mock_client = mock.patch.object(k8s_service, "Kubernetes")
        self.client_cls = p_mock_client.start()
        self.client = self.client_cls.return_value
        self.addCleanup(p_mock_client.stop)

        self.ctx = namespaces.NamespaceContext(dict(
            env={"platforms": {"kubernetes": {}}}
        ))

    def test_create_single_namespace_without_sa(self):
        self.client_cls.reset_mock()
        self.client.create_namespace.return_value = "test"

        old_config = copy.deepcopy(self.ctx.config)
        old_config.update({"count": 1})
        self.ctx.config = old_config
        self.ctx.setup()

        self.assertEqual(["test"],
                         self.ctx.context["kubernetes"]["namespaces"])
        self.assertEqual(
            "random",
            self.ctx.context["kubernetes"]["namespace_choice_method"]
        )
        self.assertFalse(self.ctx.context["kubernetes"]["serviceaccounts"])

        self.client.create_namespace.assert_called_once()
        self.assertEqual(0, self.client.create_serviceaccount.call_count)
        self.assertEqual(0, self.client.create_secret.call_count)

    def test_create_several_namespaces_without_sa(self):
        self.client_cls.reset_mock()
        self.client.create_namespace.side_effect = ["test1", "test2", "test3"]

        old_config = copy.deepcopy(self.ctx.config)
        old_config.update({"count": 3})
        self.ctx.config = old_config
        self.ctx.setup()

        self.assertEqual(["test1", "test2", "test3"],
                         self.ctx.context["kubernetes"]["namespaces"])
        self.assertEqual(
            "random",
            self.ctx.context["kubernetes"]["namespace_choice_method"]
        )
        self.assertFalse(self.ctx.context["kubernetes"]["serviceaccounts"])

        self.assertEqual(3, self.client.create_namespace.call_count)
        self.assertEqual(0, self.client.create_serviceaccount.call_count)
        self.assertEqual(0, self.client.create_secret.call_count)

    def test_create_single_namespace_with_sa_and_round_choice(self):
        self.client_cls.reset_mock()
        self.client.create_namespace.return_value = "test"

        old_config = copy.deepcopy(self.ctx.config)
        old_config.update({
            "count": 1,
            "with_serviceaccount": True,
            "namespace_choice_method": "round_robin"
        })
        self.ctx.config = old_config
        self.ctx.setup()

        self.assertEqual(["test"],
                         self.ctx.context["kubernetes"]["namespaces"])
        self.assertEqual(
            "round_robin",
            self.ctx.context["kubernetes"]["namespace_choice_method"]
        )
        self.assertTrue(self.ctx.context["kubernetes"]["serviceaccounts"])

        self.client.create_namespace.assert_called_once()
        self.client.create_serviceaccount.assert_called_once_with(
            "test",
            namespace="test"
        )
        self.client.create_secret.assert_called_once_with(
            "test",
            namespace="test"
        )

    def test_create_several_namespaces_with_sa_and_round_choice(self):
        self.client_cls.reset_mock()
        self.client.create_namespace.side_effect = ["test1", "test2", "test3"]

        old_config = copy.deepcopy(self.ctx.config)
        old_config.update({
            "count": 3,
            "with_serviceaccount": True,
            "namespace_choice_method": "round_robin"
        })
        self.ctx.config = old_config
        self.ctx.setup()

        self.assertEqual(["test1", "test2", "test3"],
                         self.ctx.context["kubernetes"]["namespaces"])
        self.assertEqual(
            "round_robin",
            self.ctx.context["kubernetes"]["namespace_choice_method"]
        )
        self.assertTrue(self.ctx.context["kubernetes"]["serviceaccounts"])

        self.assertEqual(3, self.client.create_namespace.call_count)
        self.assertEqual(3, self.client.create_serviceaccount.call_count)
        self.assertEqual(3, self.client.create_secret.call_count)
