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

import mock

from tests.unit import test
from xrally_kubernetes.tasks.scenarios import namespaces


class ListNamespacesTestCase(test.TestCase):

    def test_list(self):
        client = mock.MagicMock()
        client.list_namespaces.return_value = [
            {"name": "a", "uid": 1, "labels": {"test": "stub"}},
            {"name": "b", "uid": 2, "labels": {"test": "stub"}}
        ]

        scenario = namespaces.ListNamespaces()
        scenario.client = client

        scenario.run()

        client.list_namespaces.assert_called_once()

        self.assertEqual([], scenario._output["additive"])
        self.assertEqual([{
            "title": "Namespaces",
            "description": "A list of available namespaces.",
            "chart_plugin": "Table",
            "data": {
                "cols": ["Name", "UID", "Labels"],
                "rows": [["a", 1, {"test": "stub"}],
                         ["b", 2, {"test": "stub"}]]
            }
        }], scenario._output["complete"])

    def test_list_empty(self):
        client = mock.MagicMock()
        client.list_namespaces.return_value = []

        scenario = namespaces.ListNamespaces()
        scenario.client = client

        scenario.run()

        client.list_namespaces.assert_called_once()

        self.assertEqual([], scenario._output["additive"])
        self.assertEqual([{
            "title": "Namespaces",
            "chart_plugin": "TextArea",
            "data": ["No namespaces are available."]
        }], scenario._output["complete"])
