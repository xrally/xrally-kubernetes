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

import itertools
import json
import os
import traceback

import mock
import yaml

from rally import api
from rally.env import env_mgr
from rally.task import context
from rally.task import engine
from rally.task import scenario

from tests.unit import test
import xrally_kubernetes

ROOT_PATH = os.path.dirname(os.path.dirname(xrally_kubernetes.__file__))


class SamplesTestCase(test.TestCase):
    def setUp(self):
        super(SamplesTestCase, self).setUp()
        if os.environ.get("TOX_ENV_NAME") == "cover":
            self.skipTest("There is no need to check samples in coverage job.")
        if not hasattr(self, "samples_path"):
            self.skipTest("It is a base class.")
        self.rapi = api.API(skip_db_check=True)

    def iterate_samples(self, merge_pairs=True):
        """Iterates all task samples

        :param merge_pairs: Whether or not to return both json and yaml samples
            of one sample.
        """
        for dirname, dirnames, filenames in os.walk(self.samples_path):
            for filename in filenames:
                # NOTE(hughsaunders): Skip non config files
                # (bug https://bugs.launchpad.net/rally/+bug/1314369)
                if filename.endswith("json") or (
                        not merge_pairs and filename.endswith("yaml")):
                    yield os.path.join(dirname, filename)

    def test_no_underscores_in_filename(self):
        bad_filenames = []
        for dirname, dirnames, filenames in os.walk(self.samples_path):
            for filename in filenames:
                if "_" in filename and (filename.endswith(".yaml") or
                                        filename.endswith(".json")):
                    full_path = os.path.join(dirname, filename)
                    bad_filenames.append(full_path)

        self.assertEqual([], bad_filenames,
                         "Following sample filenames contain "
                         "underscores (_) but must use dashes (-) instead: "
                         "{}".format(bad_filenames))


class EnvironmentTestCase(SamplesTestCase):
    samples_path = os.path.join(ROOT_PATH, "samples", "platform")

    def validate(self, spec, path):
        with mock.patch("rally.env.env_mgr.db.env_create"):
            try:
                env_mgr.EnvManager._validate_and_create_env(
                    self.id(), spec)
            except Exception as e:
                self.fail("Failed to validate %s spec: %s" %
                          (path, e))

    def test_envs_specs(self):
        not_equal = []
        missed = []
        samples_paths = list(self.iterate_samples(merge_pairs=False))
        for spec_path in samples_paths:
            if spec_path.endswith(".yaml"):
                json_path = spec_path.replace(".yaml", ".json")
                if json_path not in samples_paths:
                    missed.append(json_path)
                    with open(spec_path) as f:
                        spec = self.rapi.task.render_template(
                            task_template=f.read())
                        print(spec)
                        self.validate(spec, spec_path)
            else:
                yaml_path = spec_path.replace(".json", ".yaml")
                if yaml_path not in samples_paths:
                    missed.append(yaml_path)
                    continue

                with open(spec_path) as f:
                    spec_from_json = self.rapi.task.render_template(
                        task_template=f.read())
                    spec_from_json = json.loads(spec_from_json)
                yaml_path = spec_path.replace(".json", ".yaml")
                with open(yaml_path) as f:
                    spec_from_yaml = self.rapi.task.render_template(
                        task_template=f.read())
                    spec_from_yaml = yaml.safe_load(spec_from_yaml)
                if spec_from_json != spec_from_yaml:
                    not_equal.append(
                        "\n '%s' and '%s'" % (spec_path, yaml_path))
                else:
                    self.validate(spec_from_json, spec_path)
        error = ""
        if not_equal:
            error += ("Sample task configs are not equal:\n%s"
                      % "\n".join(not_equal))

        if missed:
            if error:
                error += "\n"
            error += ("Sample task configs are missing:\n\t%s\n"
                      % "\n\t".join(missed))

        if error:
            self.fail(error)


class TaskSampleTestCase(SamplesTestCase):
    samples_path = os.path.join(ROOT_PATH, "samples", "scenario")

    def test_schema_is_valid(self):
        scenarios = set()

        for path in self.iterate_samples():
            with open(path) as task_file:
                try:
                    try:
                        task_template = self.rapi.task.render_template(
                            task_template=task_file.read())
                        task_config = yaml.safe_load(task_template)
                        task_config = engine.TaskConfig(task_config)
                    except Exception:
                        print(traceback.format_exc())
                        self.fail("Invalid JSON file: %s" % path)
                    eng = engine.TaskEngine(task_config,
                                            mock.MagicMock(), mock.Mock())
                    eng.validate(only_syntax=True)
                except Exception:
                    print(traceback.format_exc())
                    self.fail("Invalid task file: %s" % path)
                else:
                    workloads = itertools.chain(
                        *[s["workloads"] for s in task_config.subtasks])
                    scenarios.update(w["name"] for w in workloads)

        missing = set(s.get_name() for s in scenario.Scenario.get_all()
                      if s.__module__.startswith("xrally_kubernetes"))
        missing -= scenarios
        if missing:
            self.fail("These scenarios don't have samples: %s" % missing)

    def test_task_config_pairs(self):

        not_equal = []
        missed = []
        checked = []

        for path in self.iterate_samples(merge_pairs=False):
            if path.endswith(".json"):
                json_path = path
                yaml_path = json_path.replace(".json", ".yaml")
            else:
                yaml_path = path
                json_path = yaml_path.replace(".yaml", ".json")

            if json_path in checked:
                continue
            else:
                checked.append(json_path)

            if not os.path.exists(yaml_path):
                missed.append(yaml_path)
            elif not os.path.exists(json_path):
                missed.append(json_path)
            else:
                with open(json_path) as json_file:
                    json_config = json.loads(
                        self.rapi.task.render_template(
                            task_template=json_file.read()))
                with open(yaml_path) as yaml_file:
                    yaml_config = yaml.safe_load(
                        self.rapi.task.render_template(
                            task_template=yaml_file.read()))
                if json_config != yaml_config:
                    not_equal.append("'%s' and '%s'" % (yaml_path, json_path))

        error = ""
        if not_equal:
            error += ("Sample task configs are not equal:\n\t%s\n"
                      % "\n\t".join(not_equal))
        if missed:
            self.fail("Sample task configs are missing:\n\t%s\n"
                      % "\n\t".join(missed))

        if error:
            self.fail(error)

    def test_context_samples_found(self):
        all_plugins = context.Context.get_all()
        context_samples_path = os.path.join(self.samples_path, "contexts")
        for p in all_plugins:
            # except contexts which belongs to tests module
            if not p.__module__.startswith("xrally_kubernetes"):
                continue
            file_name = p.get_name().replace("_", "-")
            file_path = os.path.join(context_samples_path, file_name)
            if not os.path.exists("%s.json" % file_path):
                self.fail(("There is no json sample file of %s,"
                           "plugin location: %s" %
                           (p.get_name(), p.__module__)))
