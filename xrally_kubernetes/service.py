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
from kubernetes.client.apis import core_v1_api
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
    :param status: status waiting for
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
        if resp.status.phase != status:
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


def wait_for_ready_replicas(name, read_method, resource_type=None,
                            replicas=None, **kwargs):
    """Util method for polling status until it won't be all replicas running.

    :param name: resource name
    :param read_method: method to poll
    :param resource_type: resource type for extended exceptions
    :param replicas: expected replicas for extended exceptions
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
                desired_status="%s replicas running" % replicas,
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
            if hasattr(resp.status, "phase"):
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

        if self._k8s_client_version == 3:
            api = api_client.ApiClient(config=config)
        else:
            api = api_client.ApiClient(configuration=config)

        self.api = api
        self.v1_client = core_v1_api.CoreV1Api(api)

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
    def create_namespace(self, name, status_wait=True):
        """Create namespace and wait until status phase won't be Active.

        :param name: namespace name
        :param status_wait: wait namespace for Active status
        """
        name = name or self.generate_random_name()

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
                    if item.reason == "CreateContainerError":
                        raise exceptions.RallyException(
                            message="Volume mount failed with %(reason)s and "
                                    "message: %(msg)s" % {
                                        "reason": item.reason,
                                        "msg": item.message
                                    })
        return self.v1_client.read_namespaced_pod(name, namespace=namespace)

    @atomic.action_timer("kubernetes.create_pod")
    def create_pod(self, name, image, namespace, command=None, volume=None,
                   status_wait=True):
        """Create pod and wait until status phase won't be Running.

        :param name: pod's custom name
        :param image: pod's image
        :param namespace: chosen namespace to create pod into
        :param volume: a dict, which contains `mount_path` and `volume` keys
               with parts of pod's manifest as values
        :param command: array of strings which represents container command
        :param status_wait: wait pod for Running status
        """
        name = name or self.generate_random_name()

        container_spec = {
            "name": name,
            "image": image
        }
        if command is not None and isinstance(command, (list, tuple)):
            container_spec["command"] = list(command)
        if volume and volume.get("mount_path"):
            container_spec["volumeMounts"] = volume["mount_path"]

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
                                resource_type="Pod",
                                namespace=namespace,
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
            stdout=True, tty=False)

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
    def create_rc(self, name, replicas, image, namespace, command=None,
                  status_wait=True):
        """Create RC and wait until it won't be running.

        :param name: replication controller name
        :param replicas: number of replicas
        :param image: image for each replica
        :param namespace: replication controller namespace
        :param command: array of strings representing container command
        :param status_wait: wait replication controller for actual running
               replicas
        """
        name = name or self.generate_random_name()
        app = self.generate_random_name()

        container_spec = {
            "name": name,
            "image": image
        }
        if command is not None and isinstance(command, (list, tuple)):
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
                    replicas=replicas,
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
                    replicas=replicas,
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
