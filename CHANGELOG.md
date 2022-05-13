# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.1] - 10 May 2022

### Added

* Added logic to incremement the number of opened emails for users who don't display the tracker image but do go on to click the link (fixes #19)
* Added tracking of user `position` (job title) data for display in the results

### Changed

* Campaign names are now stripped of any non-alphanumeric characters before they are used for a filename to avoid issues with special characters (fixes #30)

### Deprecated

* None

### Removed

* None

### Fixed

* Fixed incorrect totals being presented when reporting on multiple campaigns at once caused by counters and lists not being reset (fixes #21)
* Fixed submitted data being recorded in the wrong column in Excel reports (fixes #22)

### Security

* None

## [3.0] - 31 March 2019

## Added

* Added support for Gophish's "Email Reported" event.
* Added example reports from the Gophish demo database.
* Added a new report table matching each unique IP address to its matching location.
* Added `excel` output option for xlsx reports in place of the old `csv` reports.

## Changed

* Updated the Google Maps API option now that it is the Geolocate API and requires a key.

## Removed

* Dropped the MaxMind DB geolocation due to unreliability and replaced it with an option for ipinfo.io.
* Removed the csv report in favor of a much nicer xlsx workbook report.

## Fixed

* Fixed the `--complete` flag not setting the last campaign in a list to Complete.
* Fixed typos in the reports and improved formatting.
* Geolocation lookups for IP addresses are now much, much more efficient and occur only once per unique address.
