# Changelog

## 0.1.0 - Unreleased

- Add human-readable TOML case configuration.
- Add prerequisite checks and a read-only case plan.
- Generate exact daily ERA5 pressure-level and single-level CDS requests.
- Add atomic ERA5 downloads and completed-file reuse.
- Add cached official WPS mandatory geodata downloads.
- Generate synchronized WPS/WRF namelists, physics notes and provenance.
- Add an offline test suite and GitHub Actions checks.
- Reuse matching generated case files and detect configuration conflicts before
  starting an ERA5 download.
- Separate configuration replacement from explicit ERA5 redownloads.
- Avoid initializing the CDS network client when every requested GRIB file is
  already available locally.
- Select WPS `lowres` interpolation names when the low-resolution mandatory
  geodata profile is configured.
- Validate the Netherlands demonstration case with downloaded ERA5 data through
  WPS 4.6.0 and WRF 4.7.1 `real.exe`.
- Make the ERA5-reanalysis-only scope explicit and reject other forcing modes.
- Align future history files to requested output times with WRF's
  `adjust_output_times` option.
