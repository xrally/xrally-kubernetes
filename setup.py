# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import setuptools
from setuptools import find_packages


def read_data(filename):
    filename = os.path.join(os.path.dirname(__file__), filename)
    with open(filename) as f:
        return f.read()


def read_requirements(filename):
    return [l for l in read_data(filename).split("\n")
            if l and not l.startswith("#")]


# we do not have extras yet.
EXRAS_REQUIREMENTS = {}


setuptools.setup(
    setup_requires=["setuptools_scm"],
    use_scm_version=True,
    name="xrally-kubernetes",
    packages=find_packages(exclude=["tests", "tests.*"]),
    description="A set of xRally plugins to run workloads against Kubernetes "
                "platform.",
    long_description=read_data("README.md"),
    long_description_content_type="text/markdown",
    author="xRally Team",
    url="https://xrally.org/plugins/kubernetes/overview",
    license="Apache License, Version 2.0",
    entry_points={
        "rally_plugins": [
            "path = xrally_kubernetes",
            "options = xrally_kubernetes.common.opts:list_opts"
        ]
    },
    install_requires=read_requirements("requirements.txt"),
    extras_require=EXRAS_REQUIREMENTS,
    classifiers=["Intended Audience :: Developers",
                 "Intended Audience :: Information Technology",
                 "License :: OSI Approved :: Apache Software License",
                 "Operating System :: POSIX :: Linux",
                 "Programming Language :: Python",
                 "Programming Language :: Python :: 2",
                 "Programming Language :: Python :: 2.7",
                 "Programming Language :: Python :: 3",
                 "Programming Language :: Python :: 3.4",
                 "Programming Language :: Python :: 3.5",
                 "Programming Language :: Python :: 3.6"]
)
