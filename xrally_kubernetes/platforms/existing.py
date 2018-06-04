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

import traceback

from kubernetes.client.apis import version_api
from rally.env import platform

from xrally_kubernetes import kubernetesclient


@platform.configure(name="existing", platform="kubernetes")
class KubernetesPlatform(platform.Platform):
    """Default plugin for Kubernetes."""

    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "server": {
                "type": "string",
                "description": "An endpoint of Kubernetes API."
            },
            "certificate-authority": {
                "type": "string",
                "description": "Path to certificate authority"
            },
            "client-certificate": {
                "type": "string",
                "description": "Path to client's certificate."
            },
            "client-key": {
                "type": "string",
                "description": "Path to client's key."
            },
            "tls_insecure": {
                "type": "boolean",
                "description": "Whether skip or not tls verification. "
                               "Defaults to False."
            },
            "api_key": {
                "type": "string",
                "description": "API key for API key authorization"
            },
            "api_key_prefix": {
                "type": "string",
                "description": "API key prefix"
            }
        },
        "required": ["server", "certificate-authority"],
        "additionalProperties": False
    }

    def create(self):
        # NOTE(andreykurilin): Let's save only paths to ca, key and cacert
        #   instead of saving the actual content, since paths are what
        #   KubernetesClient are actually expects to see. In further
        #   development, it would be nice to hack these and store keys in the
        #   Rally database.
        self.spec.setdefault("tls_insecure", False)
        return self.spec, {}

    def destroy(self):
        # NOTE(prazumovsky): No action need to be performed.
        pass

    def check_health(self):
        """Check whatever platform is alive."""
        try:
            self.info()
        except Exception as ex:
            return {
                "available": False,
                "message": "Something went wrong: %s" % ex.message,
                "traceback": traceback.format_exc()
            }

        return {"available": True}

    def cleanup(self, task_uuid=None):
        return {
            "message": "Coming soon!",
            "discovered": 0,
            "deleted": 0,
            "failed": 0,
            "resources": {},
            "errors": []
        }

    def _get_validation_context(self):
        return {}

    def info(self):
        service = kubernetesclient.K8sClient(self.platform_data)
        version = version_api.VersionApi(service.api).get_code().to_dict()
        return {"info": version}
