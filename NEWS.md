# Unreleased Changes

* Drop support for Python 3.7 and 3.8.

# Changes in eventstreamd 2022.12.1

* Change to calendar versioning.
* Officially support Python 3.9 through 3.11.

# Changes in eventstreamd 0.6.2

* Officially support Python 3.8.

# Changes in eventstreamd 0.6.1

## Bug Fixes

* Correctly install subpackage ``evtstrd.plugins``.

# Changes in eventstreamd 0.6.0

## Incompatible Changes

* Drop Python 3.6 support.

## New Features

* Add support for authorization plugins.

## Improvements

* Correctly identify as `eventstreamd` in the `Server` HTTP header.

# Changes in eventstreamd 0.5.4

## Improvements

* Filters not support lower than and greater than.

# Changes in eventstreamd 0.5.3

## Improvements

* Improved log output.
* Improved debug mode output.

## Docker

* Support debug mode using the `DEBUG` environment variable.

# Changes in eventstreamd 0.5.2

## Improvements

* Add a debug mode, enabled with the `-d` command line flag.

# Changes in eventstreamd 0.5.1

## Bug fixes

* Graceful shutdown on `SIGTERM` and `SIGINT`.
