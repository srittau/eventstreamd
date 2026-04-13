# Changelog for eventstreamd

## Unreleased

## 2026.4.0 – 2026-04-13

### Added

* Add a `py.typed` file to indicate that the package is typed.

### Removed

* Remove support for Python 3.10.

### Fixed

* Fix runtime errors that complain about missing event loop.

## 2025.10.0

### Added

* Support Python 3.13 and 3.14.

### Removed

* Drop support for Python 3.9.

## 2023.11.0

### Added

* Support Python 3.12.

### Removed

* Drop support for Python 3.7 and 3.8.

### Fixed

* Fix exception in server cleanup in Python 3.11+.

## 2022.12.1

### Added

* Officially support Python 3.9 through 3.11.

### Changed

* Change to calendar versioning.

## 0.6.2

### Added

* Officially support Python 3.8.

## 0.6.1

### Fixed

* Correctly install subpackage `evtstrd.plugins`.

## 0.6.0

### Added

* Add support for authorization plugins.

### Changed

* Correctly identify as `eventstreamd` in the `Server` HTTP header.

### Removed

* Drop Python 3.6 support.

## 0.5.4

### Added

* Filters now support lower than and greater than.

## 0.5.3

### Added

* [docker] Support debug mode using the `DEBUG` environment variable.

### Changed

* Improved log output.
* Improved debug mode output.

## 0.5.2

### Added

* Add a debug mode, enabled with the `-d` command line flag.

## 0.5.1

### Fixed

* Graceful shutdown on `SIGTERM` and `SIGINT`.
