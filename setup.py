#!/usr/bin/env python3

import os.path
from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="eventstreamd",
    version="0.6.2",
    description="Simple Event Stream Server",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    author="Sebastian Rittau",
    author_email="srittau@rittau.biz",
    url="https://github.com/srittau/eventstreamd",
    packages=find_packages(),
    scripts=[os.path.join("bin", "eventstreamd")],
    tests_require=["asserts >= 0.6, < 0.12"],
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Internet :: WWW/HTTP",
    ],
)
