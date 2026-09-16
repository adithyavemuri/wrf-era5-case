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
- Built-in GRIB validation checks the GRIB signature and file size. The tested
  Netherlands case received the intended variables, hours and pressure levels,
  as independently inspected with the WPS GRIB reader; arbitrary future
  downloads are not yet decoded and checked field by field by this package.
- The default metgrid-level count assumes the selected 37 pressure levels plus
  a surface level. This was confirmed for the tested Netherlands case but is
  not dynamically inferred from arbitrary input files.
- The current ERA5 variable list and ERA-Interim-compatible WPS Vtable passed
  the documented WPS 4.6.0 and WRF 4.7.1 `real.exe` acceptance test. This is a
  technical workflow validation, not proof that the demonstration setup is
  scientifically suitable for a study.
- The official high-resolution WPS geodata package needs substantial storage.
