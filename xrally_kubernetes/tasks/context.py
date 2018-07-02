# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import string

from rally.common.plugin import plugin
from rally.common import validation
from rally.task import context

from xrally_kubernetes import service as k8s_service


@validation.add_default("required_kubernetes_platform")
@plugin.default_meta(inherit=False)
class BaseKubernetesContext(context.Context):

    RESOURCE_NAME_FORMAT = "c-rally-XXXXXXXX-XXXXXXXX"
    RESOURCE_NAME_ALLOWED_CHARACTERS = string.ascii_lowercase + string.digits

    CONFIG_SCHEMA = {"type": "object", "additionalProperties": False}

    def __init__(self, context=None):
        super(BaseKubernetesContext, self).__init__(context)
        self.context.setdefault("kubernetes", {})
        self.client = k8s_service.Kubernetes(
            self.env["platforms"]["kubernetes"],
            name_generator=self.generate_random_name,
            atomic_inst=self.atomic_actions()
        )
