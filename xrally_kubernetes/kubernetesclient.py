#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from kubernetes import client as k8s_config
from kubernetes.client import api_client
from kubernetes.client.apis import core_v1_api
from rally.task import service


class K8sClient(service.Service):
    """A wrapper for python kubernetes client.

    This class handles different ways for initialization of kubernetesclient.
    """

    def __init__(self, spec, name_generator=None, atomic_inst=None):
        super(K8sClient, self).__init__(None,
                                        name_generator=name_generator,
                                        atomic_inst=atomic_inst)
        self._spec = spec

        # NOTE(andreykurilin): KubernetesClient doesn't provide any __version__
        #   property to identify the client version (you are welcome to fix
        #   this code if I'm wrong). Let's check for some backward incompatible
        #   changes to identify the way to communicate with it.
        if hasattr(k8s_config, "ConfigurationObject"):
            # Actually, it is `k8sclient < 4.0.0`, so it can be
            #   kubernetesclient 2.0 or even less, but it doesn't make any
            #   difference for us
            self._k8s_client_version = 3
        else:
            self._k8s_client_version = 4

        if self._k8s_client_version == 3:
            config = k8s_config.ConfigurationObject()
        else:
            config = k8s_config.Configuration()

        config.host = self._spec["server"]
        config.ssl_ca_cert = self._spec["certificate-authority"]
        if self._spec.get("api_key") and self._spec.get("api_key_prefix"):
            config.api_key["authorization"] = self._spec["api_key"]
            config.api_key_prefix["authorization"] = self._spec[
                "api_key_prefix"]
        else:
            config.cert_file = self._spec["client-certificate"]
            config.key_file = self._spec["client-key"]
            if self._spec.get("tls_insecure", False):
                config.verify_ssl = False

        if self._k8s_client_version == 3:
            api = api_client.ApiClient(config=config)
        else:
            api = api_client.ApiClient(configuration=config)

        self.api = api
        self.v1_client = core_v1_api.CoreV1Api(api)
