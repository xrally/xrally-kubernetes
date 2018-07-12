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

import xrally_kubernetes

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


class MapKeysParameterValidator(validation.Validator):
    """Check that parameter contains specified keys.

    :param param_name: Name of parameter to validate
    :param required: List of all required keys
    :param allowed: List of all allowed keys
    :param additional: Whether additional keys are allowed. If list of allowed
           keys are specified, defaults to False, otherwise defaults to True
    :param missed: Allow to accept optional parameter
    """
    def __init__(self, param_name, required=None, allowed=None,
                 additional=True, missed=False):
        super(MapKeysParameterValidator, self).__init__()
        self.param_name = param_name
        self.required = required or []
        self.allowed = allowed or []
        self.additional = additional
        self.missed = missed

    def validate(self, context, config, plugin_cls, plugin_cfg):
        parameter = config.get("args", {}).get(self.param_name)

        if parameter:
            required_diff = set(self.required) - set(parameter.keys())
            if required_diff:
                self.fail(
                    "Required keys is missing in '%(name)s' parameter: "
                    "%(key)s" % {"name": self.param_name,
                                 "key": ", ".join(sorted(list(required_diff)))}
                )

            if self.allowed:
                allowed_diff = set(parameter.keys()) - set(self.allowed)
                if allowed_diff:
                    self.fail(
                        "Parameter '%(name)s' contains unallowed keys: "
                        "%(key)s" % {
                            "name": self.param_name,
                            "key": ", ".join(sorted(list(allowed_diff)))}
                    )
            elif not self.additional:
                diff = set(parameter.keys()) - set(self.required)
                if diff:
                    self.fail(
                        "Parameter '%(name)s' contains unallowed keys: "
                        "%(key)s" % {
                            "name": self.param_name,
                            "key": ", ".join(sorted(list(diff)))}
                    )
        elif not self.missed:
            self.fail("'%s' parameter is not defined in the task config file"
                      % self.param_name)


if xrally_kubernetes.__rally_version__ < (1, 2):
    @validation.configure(name="map_keys")
    class MapKeysParameterValidatorConfigured(MapKeysParameterValidator):
        pass
