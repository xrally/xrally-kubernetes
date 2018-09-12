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

import os
import re

from kubernetes import client as k8s_config
from kubernetes.client import api_client
from kubernetes.client.apis import apps_v1_api
from kubernetes.client.apis import batch_v1_api
from kubernetes.client.apis import core_v1_api
from kubernetes.client.apis import extensions_v1beta1_api
from kubernetes.client.apis import storage_v1_api
from kubernetes.client.apis import version_api
from kubernetes.client import rest
from kubernetes.stream import stream
from rally.common import cfg
from rally.common import logging
from rally.common import utils as commonutils
from rally import exceptions
from rally.task import atomic
from rally.task import service

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def wait_for_status(name, status, read_method, resource_type=None, **kwargs):
    """Util method for polling status until it won't be equals to `status`.

    :param name: resource name
    :param status: status waiting for (string or tuple/list)
    :param read_method: method to poll
    :param resource_type: resource type for extended exceptions
    :param kwargs: additional kwargs for read_method
    """
    sleep_time = CONF.kubernetes.status_poll_interval
    retries_total = CONF.kubernetes.status_total_retries

    commonutils.interruptable_sleep(CONF.kubernetes.start_prepoll_delay)

    i = 0
    while i < retries_total:
        resp = read_method(name=name, **kwargs)
        resp_id = resp.metadata.uid
        current_status = resp.status.phase
        if ((isinstance(status, (list, tuple)) and
             resp.status.phase not in status) or
            (isinstance(status, str) and
             resp.status.phase != status)):
            i += 1
            commonutils.interruptable_sleep(sleep_time)
        else:
            return
        if i == retries_total:
            raise exceptions.TimeoutException(
                desired_status=status,
                resource_name=name,
                resource_type=resource_type,
                resource_id=resp_id or "<no id>",
                resource_status=current_status,
                timeout=(retries_total * sleep_time))


def wait_for_ready_replicas(name, read_method, resource_type=None, **kwargs):
    """Util method for polling status until it won't be all replicas running.

    :param name: resource name
    :param read_method: method to poll
    :param resource_type: resource type for extended exceptions
    :param kwargs: additional kwargs for read_method
    """
    sleep_time = CONF.kubernetes.status_poll_interval
    retries_total = CONF.kubernetes.status_total_retries

    commonutils.interruptable_sleep(CONF.kubernetes.start_prepoll_delay)

    i = 0
    while i < retries_total:
        resp = read_method(name=name, **kwargs)
        resp_id = resp.metadata.uid
        current_replicas = resp.status.replicas
        ready_replicas = resp.status.ready_replicas
        if (current_replicas is None or
                ready_replicas is None or
                current_replicas != ready_replicas):
            i += 1
            commonutils.interruptable_sleep(sleep_time)
        else:
            return
        if i == retries_total:
            raise exceptions.TimeoutException(
                desired_status="%s replicas running" % ready_replicas,
                resource_name=name,
                resource_type=resource_type,
                resource_id=resp_id or "<no id>",
                resource_status="%s replicas running" % current_replicas,
                timeout=(retries_total * sleep_time))


def wait_for_not_found(name, read_method, resource_type=None, **kwargs):
    """Util method for polling status while resource exists.

    :param name: resource name
    :param read_method: method to poll
    :param resource_type: resource type for extended exceptions
    :param kwargs: additional kwargs for read_method
    """
    sleep_time = CONF.kubernetes.status_poll_interval
    retries_total = CONF.kubernetes.status_total_retries

    commonutils.interruptable_sleep(CONF.kubernetes.start_prepoll_delay)

    i = 0
    while i < retries_total:
        try:
            resp = read_method(name=name, **kwargs)
            resp_id = resp.metadata.uid
            if kwargs.get("replicas"):
                current_status = "%s replicas" % resp.status.replicas
            elif kwargs.get("active"):
                current_status = resp.status.active
            elif kwargs.get("daemonset"):
                current_status = "%s pods" % resp.status.number_available
            elif hasattr(resp.status, "phase"):
                current_status = resp.status.phase
            else:
                current_status = "Unknown"
        except rest.ApiException as ex:
            if ex.status == 404:
                return
            else:
                raise
        else:
            commonutils.interruptable_sleep(sleep_time)
            i += 1
        if i == retries_total:
            raise exceptions.TimeoutException(
                desired_status="Terminated",
                resource_name=name,
                resource_type=resource_type,
                resource_id=resp_id or "<no id>",
                resource_status=current_status,
                timeout=(retries_total * sleep_time))


class Kubernetes(service.Service):
    """A wrapper for python kubernetes client.

    This class handles different ways for initialization of kubernetesclient.
    """

    def __init__(self, spec, name_generator=None, atomic_inst=None):
        super(Kubernetes, self).__init__(None,
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
        if self._spec.get("api_key"):
            config.api_key = {"authorization": self._spec["api_key"]}
            if self._spec.get("api_key_prefix"):
                config.api_key_prefix = {
                    "authorization": self._spec["api_key_prefix"]}
        else:
            config.cert_file = self._spec["client-certificate"]
            config.key_file = self._spec["client-key"]
            if self._spec.get("tls_insecure", False):
                config.verify_ssl = False

        config.assert_hostname = False
        if self._k8s_client_version == 3:
            api = api_client.ApiClient(config=config)
        else:
            api = api_client.ApiClient(configuration=config)

        self.api = api
        self.v1_client = core_v1_api.CoreV1Api(api)
        self.v1beta1_ext = extensions_v1beta1_api.ExtensionsV1beta1Api(api)
        self.v1_batch = batch_v1_api.BatchV1Api(api)
        self.v1_apps = apps_v1_api.AppsV1Api(api)
        self.v1_storage = storage_v1_api.StorageV1Api(api)

    def get_version(self):
        return version_api.VersionApi(self.api).get_code().to_dict()

    @classmethod
    def create_spec_from_file(cls):
        from kubernetes.config import kube_config

        if not os.path.exists(os.path.expanduser(
                kube_config.KUBE_CONFIG_DEFAULT_LOCATION)):
            return {}

        kube_config.load_kube_config()
        k8s_cfg = k8s_config.Configuration()
        return {
            "host": k8s_cfg.host,
            "certificate-authority": k8s_cfg.ssl_ca_cert,
            "api_key": k8s_cfg.api_key,
            "api_key_prefix": k8s_cfg.api_key_prefix,
            "client-certificate": k8s_cfg.cert_file,
            "client-key": k8s_cfg.key_file,
            "tls_insecure": k8s_cfg.verify_ssl
        }

    @atomic.action_timer("kubernetes.list_namespaces")
    def list_namespaces(self):
        """List namespaces."""
        return [{"name": r.metadata.name,
                 "uid": r.metadata.uid,
                 "labels": r.metadata.labels}
                for r in self.v1_client.list_namespace().items]

    @atomic.action_timer("kubernetes.get_namespace")
    def get_namespace(self, name):
        """Get namespace status.

        :param name: namespace name
        """
        return self.v1_client.read_namespace(name)

    @atomic.action_timer("kubernetes.create_namespace")
    def create_namespace(self, status_wait=True):
        """Create namespace and wait until status phase won't be Active.

        :param status_wait: wait namespace for Active status
        """
        name = self.generate_random_name()

        manifest = {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {
                "name": name,
                "labels": {
                    "role": name
                }
            }
        }
        self.v1_client.create_namespace(body=manifest)

        if status_wait:
            with atomic.ActionTimer(self,
                                    "kubernetes.wait_for_nc_become_active"):
                wait_for_status(name,
                                resource_type="Namespace",
                                status="Active",
                                read_method=self.get_namespace)
        return name

    @atomic.action_timer("kubernetes.delete_namespace")
    def delete_namespace(self, name, status_wait=True):
        """Delete namespace and wait it's full termination.

        :param name: namespace name
        :param status_wait: wait namespace for termination
        """
        self.v1_client.delete_namespace(name=name,
                                        body=k8s_config.V1DeleteOptions())

        if status_wait:
            with atomic.ActionTimer(self,
                                    "kubernetes.wait_namespace_termination"):
                wait_for_not_found(name,
                                   resource_type="Namespace",
                                   read_method=self.get_namespace)

    @atomic.action_timer("kubernetes.create_serviceaccount")
    def create_serviceaccount(self, name, namespace):
        """Create serviceAccount for namespace.

        :param name: serviceAccount name
        :param namespace: namespace where sa should be created
        """
        sa_manifest = {
            "apiVersion": "v1",
            "kind": "ServiceAccount",
            "metadata": {
                "name": name
            }
        }
        self.v1_client.create_namespaced_service_account(namespace=namespace,
                                                         body=sa_manifest)

    @atomic.action_timer("kubernetes.create_secret")
    def create_secret(self, name, namespace):
        """Create secret with token for namespace.

        :param name: secret name
        :param namespace: namespace where secret should be created
        """
        secret_manifest = {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {
                "name": name,
                "annotations": {
                    "kubernetes.io/service-account.name": name
                }
            }
        }
        self.v1_client.create_namespaced_secret(namespace=namespace,
                                                body=secret_manifest)

    @atomic.action_timer("kubernetes.delete_secret")
    def delete_secret(self, name, namespace):
        """Delete secret.

        :param name: secret name
        :param namespace: namespace where secret should be created
        """
        self.v1_client.delete_namespaced_secret(
            name,
            namespace=namespace,
            body=k8s_config.V1DeleteOptions()
        )

    @atomic.action_timer("kubernetes.get_pod")
    def get_pod(self, name, namespace, **kwargs):
        """Get pod status.

        :param name: pod's name
        :param namespace: pod's namespace
        """
        if kwargs.get("volume"):
            e_list = self.v1_client.list_namespaced_event(namespace=namespace)
            for item in e_list.items:
                if item.metadata.name.startswith(name):
                    if item.reason in ("CreateContainerError", "Failed"):
                        raise exceptions.RallyException(
                            message="Volume mount failed with %(reason)s and "
                                    "message: %(msg)s" % {
                                        "reason": item.reason,
                                        "msg": item.message
                                    })
        return self.v1_client.read_namespaced_pod(name, namespace=namespace)

    @atomic.action_timer("kubernetes.create_pod")
    def create_pod(self, image, namespace, command=None, volume=None,
                   port=None, protocol=None, labels=None, name=None,
                   status_wait=True):
        """Create pod and wait until status phase won't be Running.

        :param image: pod's image
        :param namespace: chosen namespace to create pod into
        :param volume: a dict, which contains `mount_path` and `volume` keys
               with parts of pod's manifest as values
        :param name: pod's custom name
        :param port: integer that represents container port
        :param protocol: container port's protocol
        :param labels: additional labels for pod
        :param command: array of strings which represents container command
        :param status_wait: wait pod for Running status
        """
        name = name or self.generate_random_name()

        container_spec = {
            "name": name,
            "image": image
        }
        if command is not None:
            if not isinstance(command, (list, tuple)):
                raise ValueError("'command' argument should be list or tuple "
                                 "type, found %s" % type(command))
            container_spec["command"] = list(command)
        if volume and volume.get("mount_path"):
            container_spec["volumeMounts"] = volume["mount_path"]
        if port is not None and isinstance(port, int) and port > 0:
            container_spec["ports"] = [{"containerPort": port}]
            if protocol is not None:
                container_spec["ports"][0]["protocol"] = protocol

        manifest = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": name,
                "labels": {
                    "role": name
                }
            },
            "spec": {
                "serviceAccountName": namespace,
                "containers": [container_spec]
            }
        }

        if labels:
            manifest["metadata"]["labels"].update(labels)
        if not self._spec.get("serviceaccounts"):
            del manifest["spec"]["serviceAccountName"]
        if volume and volume.get("volume"):
            manifest["spec"]["volumes"] = volume["volume"]

        self.v1_client.create_namespaced_pod(body=manifest,
                                             namespace=namespace)

        if status_wait:
            with atomic.ActionTimer(self,
                                    "kubernetes.wait_for_pod_become_running"):
                wait_for_status(name,
                                status="Running",
                                read_method=self.get_pod,
                                namespace=namespace,
                                resource_type="Pod",
                                volume=volume)
        return name

    @atomic.action_timer("kube.check_volume_pod_existence")
    def check_volume_pod(self, name, namespace, check_cmd, error_regexp=None):
        """Exec check_cmd in pod and get response.

        :param name: pod's name
        :param namespace: pod's namespace
        :param check_cmd: check_cmd as array of strings
        :param error_regexp: error regexp to raise exception
        """
        resp = stream(
            self.v1_client.connect_get_namespaced_pod_exec,
            name,
            namespace=namespace,
            command=check_cmd,
            stderr=True, stdin=False,
            stdout=True, tty=False
        )

        regexp = re.search(error_regexp, resp)
        if "exec failed" in resp or (error_regexp and regexp is not None):
            raise exceptions.RallyException(
                message="Check pod's volume exec failed with error: %s" % resp
            )

    @atomic.action_timer("kubernetes.delete_pod")
    def delete_pod(self, name, namespace, status_wait=True):
        """Delete pod and wait it's full termination.

        :param name: pod's name
        :param namespace: pod's namespace
        :param status_wait: wait pod for termination
        """
        self.v1_client.delete_namespaced_pod(
            name,
            namespace=namespace,
            body=k8s_config.V1DeleteOptions()
        )

        if status_wait:
            with atomic.ActionTimer(self,
                                    "kubernetes.wait_pod_termination"):
                wait_for_not_found(name,
                                   read_method=self.get_pod,
                                   resource_type="Pod",
                                   namespace=namespace)

    @atomic.action_timer("kubernetes.get_replication_controller")
    def get_rc(self, name, namespace):
        return self.v1_client.read_namespaced_replication_controller(
            name,
            namespace=namespace
        )

    @atomic.action_timer("kubernetes.create_replication_controller")
    def create_rc(self, replicas, image, namespace, command=None,
                  status_wait=True):
        """Create RC and wait until it won't be running.

        :param replicas: number of replicas
        :param image: image for each replica
        :param namespace: replication controller namespace
        :param command: array of strings representing container command
        :param status_wait: wait replication controller for actual running
               replicas
        """
        name = self.generate_random_name()
        app = self.generate_random_name()

        container_spec = {
            "name": name,
            "image": image
        }
        if command is not None:
            if not isinstance(command, (list, tuple)):
                raise ValueError("'command' argument should be list or tuple "
                                 "type, found %s" % type(command))
            container_spec["command"] = list(command)

        manifest = {
            "apiVersion": "v1",
            "kind": "ReplicationController",
            "metadata": {
                "name": name,
            },
            "spec": {
                "replicas": replicas,
                "selector": {
                    "app": app
                },
                "template": {
                    "metadata": {
                        "name": name,
                        "labels": {
                            "app": app
                        }
                    },
                    "spec": {
                        "serviceAccountName": namespace,
                        "containers": [container_spec]
                    }
                }
            }
        }

        if not self._spec.get("serviceaccounts"):
            del manifest["spec"]["template"]["spec"]["serviceAccountName"]

        self.v1_client.create_namespaced_replication_controller(
            body=manifest,
            namespace=namespace
        )

        if status_wait:
            with atomic.ActionTimer(
                    self,
                    "kubernetes.wait_for_replication_controller_ready_replicas"
            ):
                wait_for_ready_replicas(
                    name,
                    read_method=self.get_rc,
                    resource_type="Replication controller",
                    namespace=namespace)
        return name

    @atomic.action_timer("kubernetes.scale_replication_controller")
    def scale_rc(self, name, namespace, replicas, status_wait=True):
        """Scale replication controller with number of replicas.

        :param name: replication controller name
        :param namespace: replication controller namespace
        :param replicas: number of replicas replication controller scale to
        :returns True if scale successful and False otherwise
        """
        self.v1_client.patch_namespaced_replication_controller(
            name=name,
            namespace=namespace,
            body={"spec": {"replicas": replicas}}
        )
        if status_wait:
            with atomic.ActionTimer(
                    self,
                    "kubernetes.wait_for_replication_controller_ready_replicas"
            ):
                wait_for_ready_replicas(
                    name,
                    read_method=self.get_rc,
                    resource_type="Replication controller",
                    namespace=namespace)

    @atomic.action_timer("kubernetes.delete_replication_controller")
    def delete_rc(self, name, namespace, status_wait=True):
        """Delete replication controller and optionally wait for termination.

        :param name: replication controller name
        :param namespace: replication controller namespace
        :param status_wait: wait replication controller for termination
        """
        self.v1_client.delete_namespaced_replication_controller(
            name,
            namespace=namespace,
            body=k8s_config.V1DeleteOptions()
        )
        if status_wait:
            with atomic.ActionTimer(
                    self,
                    "kubernetes.wait_for_replication_controller_termination"):
                wait_for_not_found(
                    name,
                    read_method=self.get_rc,
                    resource_type="Replication controller",
                    namespace=namespace)

    @atomic.action_timer("kubernetes.get_replicaset")
    def get_replicaset(self, name, namespace, **kwargs):
        return self.v1beta1_ext.read_namespaced_replica_set(
            name,
            namespace=namespace
        )

    @atomic.action_timer("kubernetes.create_replicaset")
    def create_replicaset(self, namespace, replicas, image, command=None,
                          status_wait=True):
        """Create replicaset and wait until it won't be ready.

        :param namespace: replicaset namespace
        :param replicas: number of replicaset replicas
        :param image: container's template image
        :param command: container's template array of strings command
        :param status_wait: wait for readiness if True
        """
        app = self.generate_random_name()
        name = self.generate_random_name()

        container_spec = {
            "name": name,
            "image": image
        }
        if command is not None:
            if not isinstance(command, (list, tuple)):
                raise ValueError("'command' argument should be list or tuple "
                                 "type, found %s" % type(command))
            container_spec["command"] = list(command)

        manifest = {
            "apiVersion": "extensions/v1beta1",
            "kind": "ReplicaSet",
            "metadata": {
                "name": name,
                "labels": {
                    "app": app
                }
            },
            "spec": {
                "replicas": replicas,
                "selector": {
                    "matchLabels": {
                        "app": app
                    }
                },
                "template": {
                    "metadata": {
                        "name": name,
                        "labels": {
                            "app": app
                        }
                    },
                    "spec": {
                        "serviceAccountName": namespace,
                        "containers": [container_spec]
                    }
                }
            }
        }

        if not self._spec.get("serviceaccounts"):
            del manifest["spec"]["template"]["spec"]["serviceAccountName"]

        self.v1beta1_ext.create_namespaced_replica_set(
            namespace=namespace,
            body=manifest
        )

        if status_wait:
            with atomic.ActionTimer(
                    self,
                    "kubernetes.wait_for_replicaset_become_ready"):
                wait_for_ready_replicas(
                    name,
                    read_method=self.get_replicaset,
                    resource_type="ReplicaSet",
                    namespace=namespace)
        return name

    @atomic.action_timer("kubernetes.scale_replicaset")
    def scale_replicaset(self, name, namespace, replicas, status_wait=True):
        self.v1beta1_ext.patch_namespaced_replica_set(
            name,
            namespace=namespace,
            body={"spec": {"replicas": replicas}}
        )
        if status_wait:
            with atomic.ActionTimer(
                    self,
                    "kubernetes.wait_for_replicaset_scale"):
                wait_for_ready_replicas(
                    name,
                    read_method=self.get_replicaset,
                    resource_type="ReplicaSet",
                    namespace=namespace)

    @atomic.action_timer("kubernetes.delete_replicaset")
    def delete_replicaset(self, name, namespace, status_wait=True):
        """Delete replicaset and optionally wait for termination

        :param name: replicaset name
        :param namespace: replicaset namespace
        :param status_wait: wait for termination if True
        """
        self.v1beta1_ext.delete_namespaced_replica_set(
            name,
            namespace=namespace,
            body=k8s_config.V1DeleteOptions()
        )
        if status_wait:
            with atomic.ActionTimer(self,
                                    "kubernetes.wait_replicaset_termination"):
                wait_for_not_found(name,
                                   read_method=self.get_replicaset,
                                   namespace=namespace,
                                   resource_type="ReplicaSet",
                                   replicas=True)

    @atomic.action_timer("kubernetes.get_deployment")
    def get_deployment(self, name, namespace, **kwargs):
        return self.v1beta1_ext.read_namespaced_deployment_status(
            name=name,
            namespace=namespace
        )

    @atomic.action_timer("kubernetes.create_deployment")
    def create_deployment(self, namespace, replicas, image, resources=None,
                          env=None, command=None, status_wait=True):
        """Create deployment and wait until it won't be ready.

        :param namespace: deployment namespace
        :param replicas: number of deployment replicas
        :param image: container's template image
        :param resources: container's template resources requirements
        :param env: container's template env variables array
        :param command: container's template array of strings command
        :param status_wait: wait for readiness if True
        """
        app = self.generate_random_name()
        name = self.generate_random_name()

        container_spec = {
            "name": name,
            "image": image
        }
        if command is not None:
            if not isinstance(command, (list, tuple)):
                raise ValueError("'command' argument should be list or tuple "
                                 "type, found %s" % type(command))
            container_spec["command"] = list(command)
        if env is not None:
            if not isinstance(env, (list, tuple)):
                raise ValueError("'env' argument should be list or tuple "
                                 "type, found %s" % type(env))
            container_spec["env"] = list(env)
        if resources is not None:
            if not isinstance(resources, dict):
                raise ValueError("'resources' argument should be dict type, "
                                 "found %s" % type(resources))
            container_spec["resources"] = resources

        manifest = {
            "apiVersion": "extensions/v1beta1",
            "kind": "Deployment",
            "metadata": {
                "name": name,
                "labels": {
                    "app": app
                }
            },
            "spec": {
                "replicas": replicas,
                "template": {
                    "metadata": {
                        "name": name,
                        "labels": {
                            "app": app
                        }
                    },
                    "spec": {
                        "serviceAccountName": namespace,
                        "containers": [container_spec]
                    }
                }
            }
        }

        if not self._spec.get("serviceaccounts"):
            del manifest["spec"]["template"]["spec"]["serviceAccountName"]

        self.v1beta1_ext.create_namespaced_deployment(
            namespace=namespace,
            body=manifest
        )

        if status_wait:
            with atomic.ActionTimer(
                    self,
                    "kubernetes.wait_for_deployment_become_ready"):
                wait_for_ready_replicas(
                    name,
                    read_method=self.get_deployment,
                    resource_type="Deployment",
                    namespace=namespace)
        return name

    @atomic.action_timer("kubernetes.rollout_deployment")
    def rollout_deployment(self, name, namespace, changes, replicas,
                           status_wait=True):
        """Patch deployment and optionally wait for status.

        :param name: deployment name
        :param namespace: deployment namespace
        :param changes: map of changes, where could be image, env or resources
               requirements
        :param replicas: deployment replicas for status
        :param status_wait: wait for status if True
        """
        deployment = self.get_deployment(name, namespace=namespace)
        if changes.get("image"):
            deployment.spec.template.spec.containers[0].image = (
                changes.get("image"))
        elif changes.get("env"):
            deployment.spec.template.spec.containers[0].env = (
                changes.get("env"))
        elif changes.get("resources"):
            deployment.spec.template.spec.containers[0].resources = (
                changes.get("resources"))
        else:
            raise exceptions.InvalidArgumentsException(
                message="'changes' argument is a map with allowed mutually "
                        "exclusive keys: image, env, resources."
            )

        self.v1beta1_ext.patch_namespaced_deployment(
            name=name,
            namespace=namespace,
            body=deployment
        )
        if status_wait:
            with atomic.ActionTimer(
                    self,
                    "kubernetes.wait_for_deployment_rollout"):
                wait_for_ready_replicas(
                    name,
                    read_method=self.get_deployment,
                    resource_type="Deployment",
                    namespace=namespace)

    @atomic.action_timer("kubernetes.delete_deployment")
    def delete_deployment(self, name, namespace, status_wait=True):
        """Delete deployment and optionally wait for termination

        :param name: deployment name
        :param namespace: deployment namespace
        :param status_wait: wait for termination if True
        """
        self.v1beta1_ext.delete_namespaced_deployment(
            name=name,
            namespace=namespace,
            body=k8s_config.V1DeleteOptions()
        )
        if status_wait:
            with atomic.ActionTimer(self,
                                    "kubernetes.wait_deployment_termination"):
                wait_for_not_found(name,
                                   read_method=self.get_deployment,
                                   namespace=namespace,
                                   resource_type="Deployment",
                                   replicas=True)

    @atomic.action_timer("kubernetes.create_configmap")
    def create_configmap(self, name, namespace, data):
        """Create configMap resource.

        :param name: configMap resource name
        :param namespace: configMap namespace
        :param data: configMap data
        """
        manifest = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": name
            },
            "data": data
        }
        self.v1_client.create_namespaced_config_map(namespace=namespace,
                                                    body=manifest)

    @atomic.action_timer("kubernetes.delete_configmap")
    def delete_configmap(self, name, namespace):
        """Delete configMap resource.

        :param name: configMap name
        :param namespace: configMap namespace
        """
        self.v1_client.delete_namespaced_config_map(
            name,
            namespace=namespace,
            body=k8s_config.V1DeleteOptions()
        )

    @atomic.action_timer("kubernetes.get_job")
    def get_job(self, name, namespace, **kwargs):
        return self.v1_batch.read_namespaced_job(name, namespace=namespace)

    @atomic.action_timer("kubernetes.create_job")
    def create_job(self, namespace, image, command, name=None,
                   status_wait=True):
        """Create job and optionally wait for status.

        :param namespace: job chosen namespace
        :param image: job container's image
        :param command: job container's command
        :param name: job custom name
        :param status_wait: wait for status if True
        :return: name
        """
        name = name or self.generate_random_name()

        if not isinstance(command, (list, tuple)):
            raise ValueError("'command' argument should be list or tuple "
                             "type, found %s" % type(command))

        manifest = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "name": name
            },
            "spec": {
                "template": {
                    "metadata": {
                        "name": name
                    },
                    "spec": {
                        "restartPolicy": "Never",
                        "serviceAccountName": namespace,
                        "containers": [
                            {
                                "name": name,
                                "image": image,
                                "command": command
                            }
                        ]
                    }
                }
            }
        }

        if not self._spec.get("serviceaccounts"):
            del manifest["spec"]["template"]["spec"]["serviceAccountName"]

        self.v1_batch.create_namespaced_job(namespace=namespace, body=manifest)

        if status_wait:
            with atomic.ActionTimer(self, "kubernetes.wait_job_for_success"):
                sleep_time = CONF.kubernetes.status_poll_interval
                retries_total = CONF.kubernetes.status_total_retries

                commonutils.interruptable_sleep(
                    CONF.kubernetes.start_prepoll_delay)

                i = 0
                while i < retries_total:
                    resp = self.get_job(name=name, namespace=namespace)
                    resp_id = resp.metadata.uid
                    current_status = resp.status.succeeded
                    if current_status != 1:
                        i += 1
                        commonutils.interruptable_sleep(sleep_time)
                    else:
                        break
                    if i == retries_total:
                        raise exceptions.TimeoutException(
                            desired_status="1 succeeded",
                            resource_name=name,
                            resource_type="Job",
                            resource_id=resp_id or "<no id>",
                            resource_status="%s succeeded" % current_status,
                            timeout=(retries_total * sleep_time))
        return name

    @atomic.action_timer("kubernetes.delete_job")
    def delete_job(self, name, namespace, status_wait=True):
        """Delete job and optionally wait for termination.

        :param name: job name
        :param namespace: job namespace
        :param status_wait: wait for termination if True
        """
        self.v1_batch.delete_namespaced_job(
            name,
            namespace=namespace,
            body=k8s_config.V1DeleteOptions()
        )

        if status_wait:
            with atomic.ActionTimer(self,
                                    "kubernetes.wait_job_for_termination"):
                wait_for_not_found(name,
                                   read_method=self.get_job,
                                   resource_type="Job",
                                   namespace=namespace,
                                   active=True)

    @atomic.action_timer("kubernetes.get_statefulset")
    def get_statefulset(self, name, namespace):
        return self.v1_apps.read_namespaced_stateful_set(
            name,
            namespace=namespace
        )

    @atomic.action_timer("kubernetes.create_statefulset")
    def create_statefulset(self, namespace, replicas, image, command=None,
                           status_wait=True):
        """Create statefulset and optionally wait for ready replicas.

        :param namespace: statefulset namespace
        :param replicas: statefulset number of replicas
        :param image: container's template image
        :param command: container's template array of strings command
        :param status_wait: wait for ready replicas if True
        """
        app = self.generate_random_name()
        name = self.generate_random_name()

        container_spec = {
            "name": name,
            "image": image
        }
        if command is not None:
            if not isinstance(command, (list, tuple)):
                raise ValueError("'command' argument should be list or tuple "
                                 "type, found %s" % type(command))
            container_spec["command"] = list(command)

        manifest = {
            "apiVersion": "apps/v1",
            "kind": "StatefulSet",
            "metadata": {
                "name": name,
                "labels": {
                    "app": app
                }
            },
            "spec": {
                "selector": {
                    "matchLabels": {
                        "app": app
                    }
                },
                "replicas": replicas,
                "template": {
                    "metadata": {
                        "name": name,
                        "labels": {
                            "app": app
                        }
                    },
                    "spec": {
                        "serviceAccountName": namespace,
                        "containers": [container_spec]
                    }
                }
            }
        }

        if not self._spec.get("serviceaccounts"):
            del manifest["spec"]["template"]["spec"]["serviceAccountName"]

        self.v1_apps.create_namespaced_stateful_set(
            namespace=namespace,
            body=manifest
        )

        if status_wait:
            with atomic.ActionTimer(
                    self,
                    "kubernetes.wait_statefulset_for_ready_replicas"):
                wait_for_ready_replicas(name,
                                        read_method=self.get_statefulset,
                                        resource_type="StatefulSet",
                                        namespace=namespace)
        return name

    @atomic.action_timer("kubernetes.scale_statefulset")
    def scale_statefulset(self, name, namespace, replicas,
                          status_wait=True):
        """Scale statefulset to scale_replicas and optionally wait for status.

        :param name: statefulset name
        :param namespace: statefulset namespace
        :param replicas: statefulset replicas scale to
        :param status_wait: wait for ready scaling if True
        """
        self.v1_apps.patch_namespaced_stateful_set(
            name,
            namespace=namespace,
            body={"spec": {"replicas": replicas}}
        )

        if status_wait:
            with atomic.ActionTimer(
                    self,
                    "kubernetes.wait_statefulset_for_ready_replicas"):
                wait_for_ready_replicas(name,
                                        read_method=self.get_statefulset,
                                        resource_type="StatefulSet",
                                        namespace=namespace)

    @atomic.action_timer("kubernetes.delete_statefulset")
    def delete_statefulset(self, name, namespace, status_wait=True):
        """Delete statefulset and optionally wait for termination.

        :param name: statefulset name
        :param namespace: statefulset namespace
        :param status_wait: wait for ready scaling if True
        """
        self.v1_apps.delete_namespaced_stateful_set(
            name,
            namespace=namespace,
            body=k8s_config.V1DeleteOptions()
        )

        if status_wait:
            with atomic.ActionTimer(
                    self,
                    "kubernetes.wait_statefulset_for_termination"):
                wait_for_not_found(name,
                                   read_method=self.get_statefulset,
                                   resource_type="StatefulSet",
                                   namespace=namespace)

    @atomic.action_timer("kubernetes.list_nodes")
    def list_nodes(self, node_labels=None):
        """Return list of optionally filtered nodes names.

        :param node_labels: map, each key is a label name with some value
        """
        node_meta = [node.metadata
                     for node in self.v1_client.list_node().items]
        if node_labels is None:
            return [meta.name for meta in node_meta]

        node_names = []
        for meta in node_meta:
            for k, v in meta.labels.items():
                if k in node_labels and node_labels[k] == v:
                    node_names.append(meta.name)
        return node_names

    @atomic.action_timer("kubernetes.get_daemonset")
    def get_daemonset(self, name, namespace, **kwargs):
        return self.v1beta1_ext.read_namespaced_daemon_set(
            name,
            namespace=namespace
        )

    @atomic.action_timer("kubernetes.create_daemonset")
    def create_daemonset(self, image, namespace, command=None,
                         node_labels=None, status_wait=True):
        """Create daemon set and optionally wait for status.

        :param namespace: daemon set namespace
        :param image: daemon set template image
        :param command: daemon set template command
        :param node_labels: map, each key is a label name with some value
        :param status_wait: wait for status if True
        :return: name and app
        """
        name = self.generate_random_name()
        app = self.generate_random_name()

        container_spec = {
            "name": name,
            "image": image
        }
        if command is not None:
            if not isinstance(command, (list, tuple)):
                raise ValueError("'command' argument should be list or tuple "
                                 "type, found %s" % type(command))
            container_spec["command"] = list(command)

        manifest = {
            "apiVersion": "extensions/v1beta1",
            "kind": "DaemonSet",
            "metadata": {
                "name": name
            },
            "spec": {
                "template": {
                    "metadata": {
                        "name": name,
                        "labels": {
                            "app": app
                        }
                    },
                    "spec": {
                        "serviceAccountName": namespace,
                        "containers": [container_spec]
                    }
                }
            }
        }

        if not self._spec.get("serviceaccounts"):
            del manifest["spec"]["template"]["spec"]["serviceAccountName"]

        self.v1beta1_ext.create_namespaced_daemon_set(
            namespace=namespace,
            body=manifest
        )

        if status_wait:
            with atomic.ActionTimer(
                    self,
                    "kubernetes.wait_for_daemonset_ready_pods"):
                sleep_time = CONF.kubernetes.status_poll_interval
                retries_total = CONF.kubernetes.status_total_retries

                commonutils.interruptable_sleep(
                    CONF.kubernetes.start_prepoll_delay)

                i = 0
                while i < retries_total:
                    resp = self.get_daemonset(name=name, namespace=namespace)
                    resp_id = resp.metadata.uid
                    current_status = resp.status.number_ready
                    nodes_total = len(self.list_nodes(node_labels))
                    if current_status != nodes_total:
                        i += 1
                        commonutils.interruptable_sleep(sleep_time)
                    else:
                        break
                    if i == retries_total:
                        raise exceptions.TimeoutException(
                            desired_status="%s pods" % nodes_total,
                            resource_name=name,
                            resource_type="DaemonSet",
                            resource_id=resp_id or "<no id>",
                            resource_status="%s pods" % current_status,
                            timeout=(retries_total * sleep_time))
        return name, app

    @atomic.action_timer("kubernetes.check_daemonset_pods")
    def check_daemonset(self, namespace, app, node_labels=None):
        node_names = self.list_nodes(node_labels)

        pods = self.v1_client.list_namespaced_pod(
            namespace=namespace,
            label_selector="app=%s" % app
        )
        pods_nodes = set()
        for pod in pods.items:
            pods_nodes.add(pod.spec.node_name)

        if set(node_names).symmetric_difference(pods_nodes):
            raise exceptions.RallyException(
                message="DaemonSet check failed: number of selected nodes not "
                        "equals to number of daemonSet pods")

    @atomic.action_timer("kubernetes.delete_daemonset")
    def delete_daemonset(self, name, namespace, status_wait=True):
        """Delete daemon set and optionally wait for termination.

        :param name: daemon set name
        :param namespace: daemon set namespace
        :param status_wait: wait for termination if True
        """
        self.v1beta1_ext.delete_namespaced_daemon_set(
            name,
            namespace=namespace,
            body=k8s_config.V1DeleteOptions()
        )

        if status_wait:
            with atomic.ActionTimer(
                    self,
                    "kubernetes.wait_daemonset_for_termination"):
                wait_for_not_found(name,
                                   read_method=self.get_daemonset,
                                   resource_type="DaemonSet",
                                   namespace=namespace,
                                   daemonset=True)

    @atomic.action_timer("kubernetes.get_service")
    def get_service(self, name, namespace):
        return self.v1_client.read_namespaced_service(
            name,
            namespace=namespace
        )

    @atomic.action_timer("kubernetes.create_service")
    def create_service(self, name, namespace, port, protocol, type,
                       labels=None):
        """Create service with some type, port and protocol.

        :param name: service name
        :param namespace: service namespace
        :param port: service port
        :param protocol: service port protocol
        :param type: service type, e.g. ClusterIP or NodePort
        :param labels: labels for service selector
        """
        manifest = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": name,
                "labels": labels
            },
            "spec": {
                "type": type,
                "ports": [
                    {
                        "port": port,
                        "protocol": protocol
                    }
                ],
                "selector": labels
            }
        }

        self.v1_client.create_namespaced_service(
            namespace=namespace,
            body=manifest
        )

    @atomic.action_timer("kubernetes.get_endpoints")
    def get_endpoints(self, name, namespace):
        return self.v1_client.read_namespaced_endpoints(
            name=name,
            namespace=namespace
        )

    @atomic.action_timer("kubernetes.create_endpoints")
    def create_endpoints(self, name, namespace, ip, port):
        manifest = {
            "apiVersion": "v1",
            "kind": "Endpoints",
            "metadata": {
                "name": name
            },
            "subsets": [
                {
                    "addresses": [
                        {
                            "ip": ip
                        }
                    ],
                    "ports": [
                        {
                            "port": port
                        }
                    ]
                }
            ]
        }
        self.v1_client.create_namespaced_endpoints(
            namespace=namespace,
            body=manifest
        )

    @atomic.action_timer("kubernetes.delete_endpoints")
    def delete_endpoints(self, name, namespace):
        self.v1_client.delete_namespaced_endpoints(
            name,
            namespace=namespace,
            body=k8s_config.V1DeleteOptions()
        )

    @atomic.action_timer("kubernetes.delete_service")
    def delete_service(self, name, namespace):
        self.v1_client.delete_namespaced_service(
            name,
            namespace=namespace,
            body=k8s_config.V1DeleteOptions()
        )

    @atomic.action_timer("kubernetes.create_local_storageclass")
    def create_local_storageclass(self):
        name = self.generate_random_name()

        manifest = {
            "kind": "StorageClass",
            "apiVersion": "storage.k8s.io/v1",
            "metadata": {
                "name": name
            },
            "provisioner": "kubernetes.io/no-provisioner",
            "volumeBindingMode": "WaitForFirstConsumer"
        }

        self.v1_storage.create_storage_class(body=manifest)
        return name

    @atomic.action_timer("kubernetes.delete_local_storageclass")
    def delete_local_storageclass(self, name):
        self.v1_storage.delete_storage_class(
            name,
            body=k8s_config.V1DeleteOptions()
        )

    @atomic.action_timer("kubernetes.create_local_persistent_volume")
    def create_local_pv(self, name, storage_class, size, volume_mode,
                        local_path, access_modes, node_affinity,
                        status_wait=True):
        """Create local persistent volume and optionally wait for readiness.

        :param name: local PV name
        :param storage_class: storageClass created for local PV
        :param size: PV size (see kubernetes docs)
        :param volume_mode: PV volume mode (see kubernetes docs)
        :param local_path: local path on host to bind
        :param access_modes: array of strings - access modes (see kubernetes
               docs)
        :param node_affinity: map represents PV nodeAffinity (see kubernetes
               docs)
        :param status_wait: wait for status if True
        :return: name
        """
        name = name or self.generate_random_name()

        manifest = {
            "kind": "PersistentVolume",
            "apiVersion": "v1",
            "metadata": {
                "name": name
            },
            "spec": {
                "capacity": {
                    "storage": size
                },
                "volumeMode": volume_mode,
                "accessModes": access_modes,
                "persistentVolumeReclaimPolicy": "Retain",
                "storageClassName": storage_class,
                "local": {
                    "path": local_path
                },
                "nodeAffinity": node_affinity
            }
        }

        self.v1_client.create_persistent_volume(body=manifest)

        if status_wait:
            with atomic.ActionTimer(
                    self,
                    "kubernetes.wait_for_local_persistent_volume_become_ready"
            ):
                wait_for_status(name,
                                status=("Available", "Released"),
                                read_method=self.get_local_pv,
                                resource_type="Persistent Volume")
        return name

    @atomic.action_timer("kubernetes.get_local_persistent_volume")
    def get_local_pv(self, name):
        return self.v1_client.read_persistent_volume(name)

    @atomic.action_timer("kubernetes.delete_local_persistent_volume")
    def delete_local_pv(self, name, status_wait=True):
        """Delete local PV and optionally wait for not found it.

        :param name: local PV name
        :param status_wait: wait for termination if True
        """
        self.v1_client.delete_persistent_volume(
            name=name,
            body=k8s_config.V1DeleteOptions()
        )

        if status_wait:
            with atomic.ActionTimer(
                self,
                "kubernetes.wait_for_local_persistent_volume_termination"
            ):
                wait_for_not_found(name,
                                   read_method=self.get_local_pv,
                                   resource_type="Persistent Volume")

    @atomic.action_timer("kubernetes.create_local_persistent_volume_claim")
    def create_local_pvc(self, name, namespace, storage_class, access_modes,
                         size):
        """Create local persistent volume claim.

        :param name: local PVC name
        :param namespace: local PVC namespace
        :param storage_class: storageClass created for local PV
        :param access_modes: array of strings - access modes (see kubernetes
               docs)
        :param size: PV size (see kubernetes docs)
        :return:
        """
        manifest = {
            "kind": "PersistentVolumeClaim",
            "apiVersion": "v1",
            "metadata": {
                "name": name
            },
            "spec": {
                "resources": {
                    "requests": {
                        "storage": size
                    }
                },
                "accessModes": access_modes,
                "storageClassName": storage_class
            }
        }

        self.v1_client.create_namespaced_persistent_volume_claim(
            namespace=namespace,
            body=manifest
        )

    @atomic.action_timer("kubernetes.get_local_pvc")
    def get_local_pvc(self, name, namespace):
        return self.v1_client.read_namespaced_persistent_volume_claim(
            name, namespace=namespace)

    @atomic.action_timer("kubernetes.delete_local_pvc")
    def delete_local_pvc(self, name, namespace, status_wait=True):
        """Delete local PVC and optionally wait for termination.

        :param name: local PVC name
        :param namespace: local PVC namespace
        :param status_wait: wait for termination if True
        """
        self.v1_client.delete_namespaced_persistent_volume_claim(
            name=name,
            namespace=namespace,
            body=k8s_config.V1DeleteOptions()
        )

        if status_wait:
            with atomic.ActionTimer(
                self,
                "kubernetes.wait_for_local_persistent_volume_claim_termination"
            ):
                wait_for_not_found(name,
                                   namespace=namespace,
                                   read_method=self.get_local_pvc,
                                   resource_type="Persistent Volume Claim")
