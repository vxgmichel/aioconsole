#!/usr/bin/env python3

import sys
from setuptools import setup

TESTING = any(x in sys.argv for x in ["test", "pytest"])

README = open("README.rst").read()

CLASSIFIERS = """\
Programming Language :: Python
Programming Language :: Python :: 3
Programming Language :: Python :: 3.8
Programming Language :: Python :: 3.9
Programming Language :: Python :: 3.10
Programming Language :: Python :: 3.11
Programming Language :: Python :: 3.12
Programming Language :: Python :: 3 :: Only
""".splitlines()

setup(
    name="aioconsole",
    version="0.7.0",
    packages=["aioconsole"],
    entry_points={"console_scripts": ["apython = aioconsole:run_apython"]},
    setup_requires=["pytest-runner" if TESTING else ""],
    tests_require=[
        "pytest",
        "pytest-asyncio",
        "pytest-cov",
        "pytest-repeat",
        'uvloop; python_implementation != "PyPy" and sys_platform != "win32"',
    ],
    license="GPLv3",
    python_requires=">=3.8",
    classifiers=CLASSIFIERS,
    description="Asynchronous console and interfaces for asyncio",
    long_description=README,
    author="Vincent Michel",
    author_email="vxgmichel@gmail.com",
    url="https://github.com/vxgmichel/aioconsole",
    download_url="https://pypi.org/project/aioconsole/",
)
