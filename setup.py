# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import os
from setuptools import find_packages, setup
import sys

src_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, src_dir)
import seldon_microservice
from seldon_microservice._packaging import BuildPyCommand, SDistCommand

setup(
    name="seldon-microservice",
    author="Seldon Technologies Ltd.",
    author_email="hello@seldon.io",
    description="Seldon Microservice Wrapper",
    url="https://github.com/SeldonIO/seldon-core",
    version=seldon_microservice.__version__,
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "seldon-microservice-python = seldon_microservice.microservice:main",
            "seldon-microservice-tester = seldon_microservice.tester:main",
            "seldon-microservice-api-tester = seldon_microservice.api_tester:main",
        ],
    },
    cmdclass={
        'build_py': BuildPyCommand,
        'sdist': SDistCommand,
    },
)
