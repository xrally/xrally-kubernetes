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

from rally.common import validation

add = validation.add


@validation.configure(name="required_kubernetes_platform",
                      platform="kubernetes")
class RequiredKubernetesPlatform(validation.RequiredPlatformValidator):
    """Check for kubernetes platform in selected environment."""
    def __init__(self):
        super(RequiredKubernetesPlatform, self).__init__(platform="kubernetes")

    def validate(self, context, config, plugin_cls, plugin_cfg):
        if "kubernetes" not in context["platforms"]:
            self.fail("There is no specification for kubernetes platform in "
                      "selected environment.")
