# WRF ERA5 Case

`wrf-era5-case` prepares a transparent, reproducible, single-domain WRF case
initialized and forced by ERA5 reanalysis pressure-level and surface data. It
downloads or reuses mandatory WPS geographical data, preserves the exact CDS
requests, and generates normal human-editable `namelist.wps` and
`namelist.input` files.

Version 0.1 supports **ERA5 reanalysis forcing only**. The result is a WRF
limited-area simulation (dynamical downscaling of ERA5), not a newly generated
reanalysis product. Forecast forcing, ERA5 ensemble products, operational
analysis/forecast data and data-assimilation workflows are outside its scope.

This first release prepares inputs. It does not compile WRF, run WPS, submit a
simulation, select scientifically optimal physics, or analyse `wrfout` files.

## Prerequisite: configure CDS yourself

Before using ERA5 downloads, create your own Climate Data Store account,
accept the terms for both ERA5 datasets, and configure `~/.cdsapirc` following:

https://cds.climate.copernicus.eu/how-to-api

The package does not create, copy, display or store CDS credentials. A missing
`~/.cdsapirc` produces a direct error.

## Install without root access

```bash
./install_local.sh
. .venv/bin/activate
```

## Start safely

Copy and edit the example:

```bash
cp examples/netherlands-demo.toml my-case.toml
editor my-case.toml
```

Keep `era5.forcing_mode = "reanalysis"`; other forcing modes are rejected.

All case dates are interpreted as UTC. Explicit timezone offsets are converted
to UTC before requests and namelists are generated.

Inspect everything before downloading:

```bash
wrf-era5-case check my-case.toml
wrf-era5-case plan my-case.toml
wrf-era5-case requests my-case.toml
```

`plan` is read-only. `requests` writes the exact CDS requests as JSON but does
not contact CDS.

Prepare all inputs:

```bash
wrf-era5-case prepare my-case.toml
```

The first geodata download can be large. The `low` profile is intended for
workflow testing; use `high` as a normal research starting point.

## Individual operations

```bash
wrf-era5-case geodata status my-case.toml
wrf-era5-case geodata download my-case.toml
wrf-era5-case download-era5 my-case.toml
wrf-era5-case configure my-case.toml
```

Existing recognizable GRIB files and installed geodata are reused. Existing
generated files are reused when they match. Human-edited or stale case files
are not overwritten unless `configure --force` or `prepare --force-config` is
explicitly used. Forcing configuration never redownloads ERA5; that requires
the separate `prepare --force-era5` option.
The standalone `configure` command requires the configured geodata to be
installed so it can write the exact extracted `geog_data_path`.

## Control WRF from TOML

Physics, dynamics and selected runtime settings can be changed with exact WRF
namelist keys. Users do not need to edit the generated `namelist.input`:

```toml
[namelist.physics]
bl_pbl_physics = 1
sf_sfclay_physics = 1
sf_surface_physics = 2

[namelist.dynamics]
diff_opt = 2
km_opt = 5

[namelist.time_control]
history_interval = 60

[namelist.domains]
time_step = 54
```

Run `wrf-era5-case plan CASE.toml` to inspect all effective namelist values.
Only documented keys exposed by the package are accepted; misspelled keys and
incorrect TOML types fail before downloads or generated files are changed. See
`examples/netherlands-km5.toml` for a complete workflow configuration and
`docs/NAMELIST_CONFIGURATION.md` for the supported-key table and validation
boundary.

## Vertical grid

If `[vertical_grid]` is omitted, WRF calculates its normal default eta-level
distribution using each domain's `vertical_levels` value. An explicit
terrain-following grid can instead be supplied:

```toml
[vertical_grid]
eta_levels = [1.0, 0.98, 0.95, 0.90, 0.80, 0.65, 0.50, 0.30, 0.10, 0.05, 0.0]
```

Values must start at 1.0, end at 0.0 and decrease strictly. The number of
values must equal `vertical_levels` for every configured domain. The package
validates these structural constraints but the scientific suitability and
layer spacing remain the user's responsibility.

## One-way nested domains

Repeat `[[domain]]` to define stationary child domains. The package validates
their parent relationships and geometry, then generates synchronized WPS/WRF
arrays. See `examples/netherlands-nested.toml` and
`docs/NESTED_DOMAINS.md`. Existing single `[domain]` configurations remain
supported.

## Projection and ERA5 coverage

Set `domain.map_projection` to `lambert` (default) or `mercator`. The package
projects the four outer-domain corners, converts them back to latitude and
longitude, constructs the enclosing ERA5 rectangle and then applies
`era5.margin_degrees`. The exact requested rectangle is always shown by
`plan` before downloading.

## Generated case

```text
cases/netherlands_demo/
├── case.toml
├── namelist.wps
├── namelist.input
├── PHYSICS_PROFILE.md
├── WPS_STEPS.md
├── case-manifest.json
└── requests/
```

ERA5 and geodata live in shared directories configured in `case.toml`, rather
than being copied into each case.

## Important scientific boundary

The included `demonstration` physics profile is a visible technical starting
point. It is not automatically valid for every location, resolution, season or
research question. Inspect the generated namelist and document any changes.

The ERA5 download rectangle is a conservative geometric estimate around the
single Lambert domain. Inspect the printed north/west/south/east bounds before
submitting a large CDS request.

See [CAPABILITIES_AND_LIMITATIONS.md](docs/CAPABILITIES_AND_LIMITATIONS.md) for
the precise version 0.1 boundary.

The included Netherlands example has also been exercised end to end through
WPS and `real.exe`. See [VALIDATION.md](docs/VALIDATION.md) for the exact test
case, software versions, outputs and remaining boundary.

## Tests

```bash
python -m pytest
```

Tests never download ERA5 or WPS geodata.

## License

Released under the [MIT License](LICENSE). ERA5, WRF, WPS and downloaded data
remain subject to their respective upstream terms.
