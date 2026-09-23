# Capabilities and limitations

## Scientific scope

Version 0.2 prepares WRF limited-area simulations initialized and forced by
ERA5 reanalysis. This is commonly described as ERA5-driven dynamical
downscaling. It does not assimilate observations and therefore does not produce
a new reanalysis dataset.

## Version 0.2 supports

- Single or stationary one-way nested domains using Lambert or Mercator.
- Hourly ERA5 pressure-level and single-level GRIB requests.
- ERA5 `product_type = reanalysis` only, enforced in both configuration and CDS
  request generation.
- Exact daily request JSON records, including the simulation end time.
- The complete 37-level ERA5 pressure-level set by default.
- Official mandatory low- or high-resolution WPS geodata packages.
- Shared data caches and reuse of recognizable completed downloads.
- Human-readable `namelist.wps`, `namelist.input`, physics notes and manifest.
- Strict TOML overrides for supported `&physics`, `&dynamics`, `&time_control`
  and `&domains` keys, with the effective configuration recorded in the case
  manifest.
- Projection-aware ERA5 bounds derived from the outer-domain corners.
- Resolution-based restart intervals and optional explicit intervals.
- WRF-generated default eta levels or a structurally validated explicit
  `vertical_grid.eta_levels` array shared by all domains.
- WRF 4.7.1/WPS 4.6.0 demonstration-case preparation on Linux.
- No root access.

## Version 0.2 does not

- Create CDS accounts, accept terms, or manage API tokens.
- Compile WRF or WPS.
- Run `geogrid`, `ungrib`, `metgrid`, `real.exe` or `wrf.exe`.
- Submit or monitor cluster jobs.
- Support moving nests, two-way feedback, global domains, forcing datasets
  other than ERA5 pressure/single levels, or data assimilation.
- Support forecast products, ERA5 ensemble products, or operational
  analysis/forecast forcing.
- Select scientifically optimal physics.
- Prove that the generated case is scientifically valid.
- Produce or analyse `wrfout` files.

## Known technical boundaries

- ERA5 coverage is derived from the projected outer-domain corners for the
  supported Lambert and Mercator projections, then expanded by the configured
  safety margin.
- Built-in GRIB validation checks the GRIB signature and file size. The tested
  Netherlands case received the intended variables, hours and pressure levels,
  as independently inspected with the WPS GRIB reader; arbitrary future
  downloads are not yet decoded and checked field by field by this package.
- The default metgrid-level count assumes the selected 37 pressure levels plus
  a surface level. This was confirmed for the tested Netherlands case but is
  not dynamically inferred from arbitrary input files.
- The ERA5 variable list and combined `Vtable.ECMWF` preprocessing route passed
  an end-to-end WPS 4.6.0 and WRF 4.7.1 acceptance run through `wrf.exe` and
  report generation. This is technical workflow validation, not proof that
  the demonstration setup is scientifically suitable for a study.
- The official high-resolution WPS geodata package needs substantial storage.
- The TOML namelist interface intentionally exposes a reviewed subset of WRF
  keys. It validates names and basic value types, but it does not yet prove the
  scientific or cross-option compatibility of every accepted combination.
- Explicit eta levels are checked for ordering, endpoints and length, not for
  scientifically appropriate layer thickness or numerical stability.
