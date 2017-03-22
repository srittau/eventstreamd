#!/usr/bin/python3

import os.path
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="eventstreamd",
    version="0.5.0",
    description="Simple Event Stream Server",
    long_description=read("README.md"),
    author="Sebastian Rittau",
    author_email="srittau@rittau.biz",
    url="https://github.com/srittau/eventstreamd",
    packages=["evtstrd", "evtstrd_test"],
    scripts=[os.path.join("bin", "eventstreamd")],
    tests_require=["asserts >= 0.6"],
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Topic :: Internet :: WWW/HTTP",
    ],
)
