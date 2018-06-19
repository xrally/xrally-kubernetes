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
import traceback

from rally.env import platform

from xrally_kubernetes import service as k8s_service


@platform.configure(name="existing", platform="kubernetes")
class KubernetesPlatform(platform.Platform):
    """Default plugin for Kubernetes."""

    CONFIG_SCHEMA = {
        "type": "object",
        "oneOf": [
            {
                "description": "The auth-token authentication",
                "properties": {
                    "server": {
                        "type": "string",
                        "description": "An endpoint of Kubernetes API."
                    },
                    "certificate-authority": {
                        "type": "string",
                        "description": "Path to certificate authority"
                    },
                    "api_key": {
                        "type": "string",
                        "description": "API key for API key authorization"
                    },
                    "api_key_prefix": {
                        "type": "string",
                        "description": "API key prefix. Defaults to 'Bearer'."
                    }
                },
                "required": ["server", "certificate-authority", "api_key"],
                "additionalProperties": False
            },
            {
                "description": "The authentication via client certificates.",
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
                },
                "required": ["server", "certificate-authority",
                             "client-certificate", "client-key"],
                "additionalProperties": False
            }
        ]
    }

    def create(self):
        # NOTE(andreykurilin): Let's save only paths to ca, key and cacert
        #   instead of saving the actual content, since paths are what
        #   KubernetesClient are actually expects to see. In further
        #   development, it would be nice to hack these and store keys in the
        #   Rally database.
        for key in ("certificate-authority", "client-certificate",
                    "client-key"):
            if key in self.spec:
                self.spec[key] = os.path.abspath(
                    os.path.expanduser(self.spec[key]))
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
                "message": "Something went wrong: %s" % ex,
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
        version = k8s_service.Kubernetes(self.platform_data).get_version()
        return {"info": version}

    @classmethod
    def _get_doc(cls):
        doc = cls.__doc__.strip()
        doc += "\n **Create a spec based on system environment.**\n"
        # cut the first line since we already included the first line of it.
        doc += "\n".join(
            [line.strip() for line in
             cls.create_spec_from_sys_environ.__doc__.split("\n")][1:])
        return doc

    @classmethod
    def create_spec_from_sys_environ(cls, sys_environ):
        """Create a spec based on system environment.

        The environment variables could be defined with two mutually exclusive
        mandatory ways: check kubeconfig file or kubeconfig envvar, defining
        certificates or defining auth token.

        To search configuration in kubeconfig file, rally checks standard
        `$HOME/.kube/config` file or get `KUBECONFIG` envvar.

        To define certificates to connect next variables used:

          .. envvar:: KUBERNETES_HOST
              The URL to the Kubernetes host.
          .. envvar:: KUBERNETES_TLS_INSECURE
              Not to verify the host against a CA certificate.
          .. envvar:: KUBERNETES_CERT_AUTH
              A path to a file containing TLS certificate to use when
              connecting to the Kubernetes host.
          .. envvar:: KUBERNETES_CLIENT_CERT
              A path to a file containing client certificate to use when
              connecting to the Kubernetes host.
          .. envvar:: KUBERNETES_CLIENT_KEY
              A path to a file containing client key to use when connecting to
              the Kubernetes host.

        To define auth token to connect next variables used:

          .. envvar:: KUBERNETES_HOST
              The URL to the Kubernetes host.
          .. envvar:: KUBERNETES_CERT_AUTH
              A path to a file containing TLS certificate to use when
              connecting to the Kubernetes host.
          .. envvar:: KUBERNETES_API_KEY
              Client API key to use as token when connecting to the Kubernetes
              host.
          .. envvar:: KUBERNETES_API_KEY_PREFIX
              Client API key prefix to use in token when connecting to the
              Kubernetes host.
        """
        k8s_cfg = k8s_service.Kubernetes.create_spec_from_file()

        host = k8s_cfg.get("host") or sys_environ.get("KUBERNETES_HOST")
        cert_auth = (k8s_cfg.get("certificate-authority") or
                     sys_environ.get("KUBERNETES_CERT_AUTH"))

        if not (host and cert_auth):
            return {
                "available": False,
                "message": "sys-env has no KUBERNETES_HOST or "
                           "KUBERNETES_CERT_AUTH vars"
            }

        cert_auth = os.path.abspath(os.path.expanduser(cert_auth))

        # If tls_insecure in env vars, True if it has any value
        tls_insecure = (k8s_cfg.get("tls_insecure") or
                        sys_environ.get("KUBERNETES_TLS_INSECURE"))
        if tls_insecure == "":
            tls_insecure = False
        else:
            tls_insecure = tls_insecure is not None

        ckey = (k8s_cfg.get("client-key") or
                sys_environ.get("KUBERNETES_CLIENT_KEY"))
        ccert = (k8s_cfg.get("client-certificate") or
                 sys_environ.get("KUBERNETES_CLIENT_CERT"))

        if ckey and ccert:
            ckey = os.path.abspath(os.path.expanduser(ckey))
            ccert = os.path.abspath(os.path.expanduser(ccert))
            return {
                "available": True,
                "spec": {
                    "server": host,
                    "certificate-authority": cert_auth,
                    "client-certificate": ccert,
                    "client-key": ckey,
                    "tls_insecure": tls_insecure
                }
            }

        if k8s_cfg.get("api_key"):
            api_key = k8s_cfg["api_key"].get("authorization")
        else:
            api_key = sys_environ.get("KUBERNETES_API_KEY")
        if k8s_cfg.get("api_key_prefix"):
            api_key_prefix = k8s_cfg["api_key_prefix"].get("authorization")
        else:
            api_key_prefix = sys_environ.get("KUBERNETES_API_KEY_PREFIX")

        if api_key:
            spec = {
                "server": host,
                "certificate-authority": cert_auth,
                "api_key": api_key
            }
            if api_key_prefix:
                spec["api_key_prefix"] = api_key_prefix
            return {
                "available": True,
                "spec": spec
            }

        return {"available": False,
                "message": "Missing required env variables: "
                           "%(crt)s or %(api)s" % {
                               "crt": ["KUBERNETES_CLIENT_CERT",
                                       "KUBERNETES_CLIENT_KEY",
                                       "KUBERNETES_TLS_INSECURE"],
                               "api": ["KUBERNETES_API_KEY",
                                       "KUBERNETES_API_KEY_PREFIX"]
                           }}
