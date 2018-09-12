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
from xrally_kubernetes.tasks.contexts import local_storageclass


class LocalStorageClassContextTestCase(test.TestCase):

    def setUp(self):
        super(LocalStorageClassContextTestCase, self).setUp()

        from xrally_kubernetes import service as k8s_service

        p_mock_client = mock.patch.object(k8s_service, "Kubernetes")
        self.client_cls = p_mock_client.start()
        self.client = self.client_cls.return_value
        self.addCleanup(p_mock_client.stop)

        self.ctx = local_storageclass.LocalStorageClassContext(dict(
            env={"platforms": {"kubernetes": {}}}
        ))

    def test_create(self):
        self.client_cls.reset_mock()
        self.client.create_local_storageclass.return_value = "test"

        self.ctx.setup()

        self.assertEqual("test",
                         self.ctx.context["kubernetes"]["storageclass"])

        self.client.create_local_storageclass.assert_called_once()

    def test_delete(self):
        self.client_cls.reset_mock()
        self.ctx.context["kubernetes"]["storageclass"] = "test"
        self.ctx.cleanup()
        self.client.delete_local_storageclass.assert_called_once_with("test")
