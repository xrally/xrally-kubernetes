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

from rally.task import context

from xrally_kubernetes.tasks import context as common_context


@context.configure("local_storageclass", order=1001, platform="kubernetes")
class LocalStorageClassContext(common_context.BaseKubernetesContext):
    """Context for creating local storageClass."""

    CONFIG_SCHEMA = {
        "type": "object",
        "additionalProperties": False,
        "properties": {}
    }

    def setup(self):
        self.context["kubernetes"].setdefault("storageclass", None)
        name = self.client.create_local_storageclass()
        self.context["kubernetes"]["storageclass"] = name

    def cleanup(self):
        self.client.delete_local_storageclass(
            self.context["kubernetes"]["storageclass"])
