# WRF ERA5 Case

`wrf-era5-case` prepares a transparent, reproducible, single-domain WRF case
from ERA5 pressure-level and surface data. It downloads or reuses mandatory
WPS geographical data, preserves the exact CDS requests, and generates normal
human-editable `namelist.wps` and `namelist.input` files.

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
generated namelists are not overwritten unless `--force` is explicitly used.
The standalone `configure` command requires the configured geodata to be
installed so it can write the exact extracted `geog_data_path`.

## Generated case

```text
cases/netherlands_demo/
├── case.toml
├── namelist.wps
├── namelist.wps.pressure
├── namelist.wps.surface
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

## Tests

```bash
python -m pytest
```

Tests never download ERA5 or WPS geodata.

## License

Released under the [MIT License](LICENSE). ERA5, WRF, WPS and downloaded data
remain subject to their respective upstream terms.
