# Changelog

## 0.2.0 - 2026-09-22

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
- Replace the legacy split preprocessing path with one combined ERA5
  `ungrib.exe` pass using the WPS-provided `Vtable.ECMWF`.
- Validate the combined preprocessing route through WPS, `real.exe`, `wrf.exe`
  and WRF_tools report generation with the Netherlands reference case.
- Add strict TOML-controlled WRF physics, dynamics, time-control and domain
  options, effective-configuration planning, and manifest provenance.
- Add backward-compatible stationary one-way nested-domain configuration,
  geometry validation and synchronized WPS/WRF namelist arrays.
- Validate the two-domain Netherlands example through WPS, `real.exe`, the
  complete nested forecast and a `d02` WRF_tools PDF report.
- Add projection-aware ERA5 bounds, configurable restart checkpoints and
  validated optional eta-level grids.

## 0.1.0
