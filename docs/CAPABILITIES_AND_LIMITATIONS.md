# Capabilities and limitations

## Version 0.1 supports

- One Lambert-projection WRF domain.
- Hourly ERA5 pressure-level and single-level GRIB requests.
- Exact daily request JSON records, including the simulation end time.
- The complete 37-level ERA5 pressure-level set by default.
- Official mandatory low- or high-resolution WPS geodata packages.
- Shared data caches and reuse of recognizable completed downloads.
- Human-readable `namelist.wps`, `namelist.input`, physics notes and manifest.
- WRF 4.7.1/WPS 4.6.0 demonstration-case preparation on Linux.
- No root access.

## Version 0.1 does not

- Create CDS accounts, accept terms, or manage API tokens.
- Compile WRF or WPS.
- Run `geogrid`, `ungrib`, `metgrid`, `real.exe` or `wrf.exe`.
- Submit or monitor cluster jobs.
- Support nests, global domains, other forcing datasets or data assimilation.
- Select scientifically optimal physics.
- Prove that the generated case is scientifically valid.
- Produce or analyse `wrfout` files.

## Known technical boundaries

- The ERA5 bounding rectangle is a conservative spherical estimate. It is not
  calculated from exact projected WRF corner coordinates.
- GRIB validation initially checks the GRIB signature and file size. Full
  variable/time/level validation requires WPS or a GRIB decoder and is a later
  milestone.
- The default metgrid-level count assumes the selected pressure levels plus a
  surface level. It must be confirmed against the actual `met_em` output.
- The ERA5 variable list and WPS Vtable path must pass the planned real WPS
  acceptance test before the package is declared production-ready.
- The official high-resolution WPS geodata package needs substantial storage.
