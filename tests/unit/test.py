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

import fixtures
from fixtures._fixtures.tempdir import TempDir

import mock
import testtools

from rally import plugins


class TempHomeDir(TempDir):
    """Create a temporary directory and set it as $HOME

    :ivar path: the path of the temporary directory.
    """

    def _setUp(self):
        super(TempHomeDir, self)._setUp()
        self.useFixture(fixtures.EnvironmentVariable("HOME", self.path))


class TestCase(testtools.TestCase):
    """Test case base class for all unit tests."""

    def __init__(self, *args, **kwargs):
        super(TestCase, self).__init__(*args, **kwargs)

        # This is the number of characters shown when two objects do not
        # match for assertDictEqual, assertMultiLineEqual, and
        # assertSequenceEqual. The default is 640 which is too
        # low for comparing most dicts
        self.maxDiff = 10000

    def setUp(self):
        super(TestCase, self).setUp()
        self.addCleanup(mock.patch.stopall)
        plugins.load()
        self.useFixture(TempHomeDir())
