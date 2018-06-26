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

import random
import string

from rally.common.plugin import plugin
from rally.common import validation
from rally.task import scenario

from xrally_kubernetes import service as k8s_service


@validation.add_default("required_kubernetes_platform")
@plugin.default_meta(inherit=False)
class BaseKubernetesScenario(scenario.Scenario):

    RESOURCE_NAME_FORMAT = "rally-XXXXXXXX-XXXXXXXX"
    RESOURCE_NAME_ALLOWED_CHARACTERS = string.ascii_lowercase + string.digits

    def choose_namespace(self):
        if self.context["kubernetes"]["namespace_choice_method"] == "random":
            return random.choice(self.context["kubernetes"]["namespaces"])
        elif (self.context["kubernetes"]["namespace_choice_method"] ==
              "round_robin"):
            idx = self.context["iteration"] - 1
            idx = idx % len(self.context["kubernetes"]["namespaces"])
            return self.context["kubernetes"]["namespaces"][idx]

    def __init__(self, context=None):
        super(BaseKubernetesScenario, self).__init__(context)
        self.context.setdefault("kubernetes", {})
        spec = {
            "namespaces": self.context["kubernetes"].get("namespaces"),
            "serviceaccounts": self.context["kubernetes"].get(
                "serviceaccounts")
        }
        if "env" in self.context:
            spec.update(self.context["env"]["platforms"]["kubernetes"])
            self.client = k8s_service.Kubernetes(
                spec,
                name_generator=self.generate_random_name,
                atomic_inst=self.atomic_actions())
