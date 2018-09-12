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

from tests.unit import test
from xrally_kubernetes.tasks import validators


class RequiredKubernetesPlatformTestCase(test.TestCase):
    def test_validate(self):
        validator = validators.RequiredKubernetesPlatform()
        validator.validate(
            {"platforms": {"kubernetes": {}}}, None, None, None)
        self.assertRaises(
            validators.validation.ValidationError,
            validator.validate, {"platforms": {}}, None, None, None)


class MapKeysParameterValidatorTestCase(test.TestCase):
    def test_validate_required(self):
        validator = validators.MapKeysParameterValidator(
            param_name="testarg",
            required=["test1", "test2", "test3"]
        )
        self.assertIsNone(
            validator.validate(None, {"args": {"testarg": {"test1": "",
                                                           "test2": "",
                                                           "test3": "",
                                                           "test4": ""}}},
                               None, None))
        msg = self.assertRaises(
            validators.validation.ValidationError,
            validator.validate, None, {"args": {"testarg": {"test1": ""}}},
            None, None
        )
        self.assertEqual("Required keys is missing in 'testarg' parameter: "
                         "test2, test3", str(msg))

        msg = self.assertRaises(
            validators.validation.ValidationError,
            validator.validate, None, {}, None, None
        )
        self.assertEqual("'testarg' parameter is not defined in "
                         "the task config file", str(msg))

    def test_validate_allowed(self):
        validator = validators.MapKeysParameterValidator(
            param_name="testarg",
            required=["test1", "test2"],
            allowed=["test1", "test2", "test3"]
        )
        self.assertIsNone(
            validator.validate(None, {"args": {"testarg": {"test1": "",
                                                           "test2": "",
                                                           "test3": ""}}},
                               None, None)
        )
        self.assertIsNone(
            validator.validate(None, {"args": {"testarg": {"test1": "",
                                                           "test2": ""}}},
                               None, None)
        )
        ex = self.assertRaises(
            validators.validation.ValidationError,
            validator.validate, None, {"args": {"testarg": {"test1": "",
                                                            "test2": "",
                                                            "test3": "",
                                                            "test4": ""}}},
            None, None)
        self.assertEqual("Parameter 'testarg' contains unallowed keys: test4",
                         str(ex))

    def test_validate_additional(self):
        validator = validators.MapKeysParameterValidator(
            param_name="testarg",
            required=["test1", "test2"],
            additional=False
        )
        ex = self.assertRaises(
            validators.validation.ValidationError,
            validator.validate, None, {"args": {"testarg": {"test1": "",
                                                            "test2": "",
                                                            "test3": "",
                                                            "test4": ""}}},
            None, None)
        self.assertEqual("Parameter 'testarg' contains unallowed keys: test3, "
                         "test4", str(ex))

    def test_validate_none_required(self):
        validator = validators.MapKeysParameterValidator(
            param_name="testarg",
            allowed=["test1", "test2"]
        )
        self.assertIsNone(
            validator.validate(None, {"args": {"testarg": {"test1": "",
                                                           "test2": ""}}},
                               None, None)
        )
        ex = self.assertRaises(
            validators.validation.ValidationError,
            validator.validate, None, {"args": {"testarg": {"test1": "",
                                                            "test2": "",
                                                            "test3": "",
                                                            "test4": ""}}},
            None, None)
        self.assertEqual("Parameter 'testarg' contains unallowed keys: test3, "
                         "test4", str(ex))
