# eventstreamd

![Supported Python Versions](https://img.shields.io/pypi/pyversions/eventstreamd)
[![GitHub](https://img.shields.io/github/release/srittau/eventstreamd/all.svg)](https://github.com/srittau/eventstreamd/releases/)
[![pypi](https://img.shields.io/pypi/v/eventstreamd.svg)](https://pypi.python.org/pypi/eventstreamd/)
[![MIT License](https://img.shields.io/github/license/srittau/eventstreamd)](https://https://github.com/srittau/eventstreamd/blob/main/LICENSE)
[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/srittau/eventstreamd/test.yml)](https://github.com/srittau/eventstreamd/actions/workflows/test.yml)

A simple event stream server. Events are sent on a Unix socket and then
distributed to all interested listeners via HTTP event streams.

Docker image available:

```bash
docker pull srittau/eventstreamd
```
