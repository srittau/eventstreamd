eventstreamd
============

.. image:: https://img.shields.io/pypi/l/eventstreamd.svg
   :target: https://pypi.python.org/pypi/eventstreamd/
.. image:: https://img.shields.io/github/release/srittau/eventstreamd/all.svg
   :target: https://github.com/srittau/eventstreamd/releases/
.. image:: https://img.shields.io/pypi/v/eventstreamd.svg
   :target: https://pypi.python.org/pypi/eventstreamd/
.. image:: https://travis-ci.org/srittau/eventstreamd.svg?branch=master
   :target: https://travis-ci.org/srittau/eventstreamd

A simple event stream server. Events are sent on a Unix socket and then
distributed to all interested listeners via HTTP event streams.

Docker image available:

.. code:: bash

    docker pull srittau/eventstreamd
