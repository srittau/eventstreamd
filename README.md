# eventstreamd

[![License](https://img.shields.io/pypi/l/eventstreamd.svg)](https://pypi.python.org/pypi/eventstreamd/)
[![GitHub](https://img.shields.io/github/release/srittau/eventstreamd/all.svg)](https://github.com/srittau/eventstreamd/releases/)
[![pypi](https://img.shields.io/pypi/v/eventstreamd.svg)](https://pypi.python.org/pypi/eventstreamd/)
[![Travis CI](https://travis-ci.org/srittau/eventstreamd.svg?branch=master)](https://travis-ci.org/srittau/eventstreamd)

A simple event stream server. Events are sent on a Unix socket and then
distributed to all interested listeners via HTTP event streams.

Docker image available:

```bash
docker pull srittau/eventstreamd
```
