#!/usr/bin/env python
from __future__ import print_function
from setuptools import setup, find_packages
import battlechess

with open("README.md", "r", encoding='utf-8') as fh:
    long_description = fh.read()

setup(
    name="battlechess",
    version=battlechess.__version__,
    author="Memory&Xinxin",
    author_email="memory_d@foxmail.com",
    description="a board game written in pygame",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    url="https://github.com/MemoryD/BattleChess",
    packages=find_packages(),
    package_dir={'battlechess': 'battlechess'},
    package_data={'battlechess': ['src/image/*']},
    install_requires=[
        "pygame >= 1.9.6",
        "twisted >= 19.10.0",
        ],
    classifiers=[
        "Topic :: Games/Entertainment ",
        'Topic :: Games/Entertainment :: Board Games',
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        'Programming Language :: Python :: Implementation :: CPython',
    ],
    python_requires='>=3.5',
)