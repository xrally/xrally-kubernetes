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

import collections
import time

from rally.task import scenario

from xrally_kubernetes.tasks import scenario as common_scenario


@scenario.configure(name="Kubernetes.create_and_delete_pod",
                    platform="kubernetes")
class CreateAndDeletePod(common_scenario.BaseKubernetesScenario):

    def _parse_pod_status_conditions(self, conditions):
        """Method for collecting pods statuses: inited, scheduled, ready."""

        def to_time(dt):
            return time.mktime(dt)

        if not conditions:
            return []

        start, finish = None, None
        stat_dict = collections.OrderedDict()
        stat_dict.update({
            "kubernetes.initialized_pod": {},
            "kubernetes.scheduled_pod": {},
            "kubernetes.created_pod": {}
        })
        for d in conditions:
            if d.type == "Initialized":
                start = init_time = to_time(d.last_transition_time.timetuple())
                stat_dict["kubernetes.initialized_pod"].update({
                    "started_at": init_time
                })
            elif d.type == "PodScheduled":
                scheduled = to_time(d.last_transition_time.timetuple())
                stat_dict["kubernetes.scheduled_pod"].update({
                    "started_at": scheduled
                })
                stat_dict["kubernetes.initialized_pod"].update({
                    "finished_at": scheduled
                })
            elif d.type == "Ready":
                finish = to_time(d.last_transition_time.timetuple())
                stat_dict["kubernetes.created_pod"].update({
                    "started_at": start,
                    "finished_at": finish
                })
                stat_dict["kubernetes.scheduled_pod"].update({
                    "finished_at": finish
                })
        return [{"name": k,
                 "started_at": v["started_at"],
                 "finished_at": v["finished_at"]}
                for k, v in stat_dict.items()]

    def _make_data_from_conditions(self, conditions):
        """Make plot data from conditions made by parse method."""
        data = [[] for _ in range(3)]
        state_map = {
            "kubernetes.initialized_pod": 0,
            "kubernetes.scheduled_pod": 1,
            "kubernetes.created_pod": 2
        }

        for e in conditions:
            duration = e["finished_at"] - e["started_at"]
            data[state_map[e["name"]]] = [e["name"], duration]
        return data

    def run(self, image, command=None, status_wait=True):
        """Create pod, wait until it won't be running and then delete it.

        :param image: pod's image
        :param command: array of strings, pod's command. Could be None if
               image have entrypoint
        :param status_wait: wait pod status after creation
        """
        namespace = self.choose_namespace()

        name = self.client.create_pod(
            image,
            namespace=namespace,
            command=command,
            status_wait=status_wait
        )

        pod = self.client.get_pod(name, namespace=namespace)
        conditions = self._parse_pod_status_conditions(pod.status.conditions)
        self.add_output(
            additive={"title": "Pod's conditions total duration",
                      "description": "Total durations for pod in each "
                                     "iteration",
                      "chart_plugin": "StackedArea",
                      "data": self._make_data_from_conditions(conditions),
                      "label": "Total seconds",
                      "axis_label": "Iteration"})

        self.client.delete_pod(
            name,
            namespace=namespace,
            status_wait=status_wait
        )
