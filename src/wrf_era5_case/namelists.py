from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path

from .config import CaseConfig
from .domain import era5_area
from .era5 import Era5Request
from .geodata import find_geodata_root


def _render(template_name: str, values: dict[str, object]) -> str:
    template = files("wrf_era5_case").joinpath(
        "templates", "demonstration", template_name
    ).read_text()
    for name, value in values.items():
        template = template.replace(f"@{name}@", str(value))
    unresolved = [part.split("@", 1)[0] for part in template.split("@")[1::2]]
    if unresolved:
        raise RuntimeError(f"unresolved template values: {', '.join(unresolved)}")
    return template


def _wps_date(value: datetime) -> str:
    return value.strftime("%Y-%m-%d_%H:%M:%S")


def _duration_values(config: CaseConfig) -> tuple[int, int, int, int]:
    remainder = config.duration_seconds
    days, remainder = divmod(remainder, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    return days, hours, minutes, seconds


def _write(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        raise RuntimeError(f"refusing to replace existing file without --force: {path}")
    path.write_text(content)


def configure_case(config: CaseConfig, requests: list[Era5Request], *, force: bool = False) -> dict[str, Path]:
    destination = config.case_directory
    destination.mkdir(parents=True, exist_ok=True)
    geog_root = find_geodata_root(config.geography_directory) or config.geography_directory
    shared = {
        "START_DATE": _wps_date(config.start),
        "END_DATE": _wps_date(config.end),
        "INTERVAL_SECONDS": config.interval_seconds,
        "E_WE": config.e_we,
        "E_SN": config.e_sn,
        "DX": f"{config.dx:g}",
        "DY": f"{config.dy:g}",
        "REF_LAT": f"{config.ref_lat:g}",
        "REF_LON": f"{config.ref_lon:g}",
        "TRUELAT1": f"{config.truelat1:g}",
        "TRUELAT2": f"{config.truelat2:g}",
        "STAND_LON": f"{config.stand_lon:g}",
        "GEOG_DATA_PATH": str(geog_root),
        "UNGRIB_PREFIX": "PRES",
    }
    days, hours, minutes, seconds = _duration_values(config)
    wrf_values = dict(shared)
    wrf_values.update({
        "RUN_DAYS": days,
        "RUN_HOURS": hours,
        "RUN_MINUTES": minutes,
        "RUN_SECONDS": seconds,
        "START_YEAR": config.start.year,
        "START_MONTH": config.start.month,
        "START_DAY": config.start.day,
        "START_HOUR": config.start.hour,
        "END_YEAR": config.end.year,
        "END_MONTH": config.end.month,
        "END_DAY": config.end.day,
        "END_HOUR": config.end.hour,
        "E_VERT": config.e_vert,
        "NUM_METGRID_LEVELS": len(config.pressure_levels) + 1,
        "HISTORY_INTERVAL": config.history_interval_minutes,
        "TIME_STEP": config.time_step_seconds,
    })

    wps_path = destination / "namelist.wps"
    wps_pressure_path = destination / "namelist.wps.pressure"
    wps_surface_path = destination / "namelist.wps.surface"
    wrf_path = destination / "namelist.input"
    config_copy = destination / "case.toml"
    profile_copy = destination / "PHYSICS_PROFILE.md"
    manifest_path = destination / "case-manifest.json"
    instructions_path = destination / "WPS_STEPS.md"
    planned = [wps_path, wps_pressure_path, wps_surface_path, wrf_path, profile_copy, instructions_path, manifest_path]
    if config.source != config_copy:
        planned.append(config_copy)
    existing = [path for path in planned if path.exists()]
    if existing and not force:
        names = ", ".join(str(path) for path in existing)
        raise RuntimeError(f"refusing to replace existing files without --force: {names}")
    pressure_wps = _render("namelist.wps.template", shared)
    surface_values = dict(shared)
    surface_values["UNGRIB_PREFIX"] = "SFC"
    surface_wps = _render("namelist.wps.template", surface_values)
    _write(wps_path, pressure_wps, force)
    _write(wps_pressure_path, pressure_wps, force)
    _write(wps_surface_path, surface_wps, force)
    _write(wrf_path, _render("namelist.input.template", wrf_values), force)
    if config.source != config_copy:
        if config_copy.exists() and not force:
            raise RuntimeError(f"refusing to replace existing file without --force: {config_copy}")
        shutil.copy2(config.source, config_copy)
    profile_text = files("wrf_era5_case").joinpath("templates", "demonstration", "README.md").read_text()
    _write(profile_copy, profile_text, force)
    instructions = f"""# WPS handoff for {config.name}

This package prepares the case but does not run WPS in version 0.1.

1. Use `namelist.wps` to run `geogrid.exe`.
2. Link WPS `Vtable.ERA-interim.pl` as `Vtable` and link the ERA5 pressure-level GRIB files.
3. Copy `namelist.wps.pressure` to the WPS working directory as `namelist.wps`; run `ungrib.exe` to create `PRES:*` files.
4. Relink the ERA5 single-level GRIB files.
5. Copy `namelist.wps.surface` to the WPS working directory as `namelist.wps`; run `ungrib.exe` to create `SFC:*` files.
6. Run `metgrid.exe`; both variants declare `fg_name = 'PRES', 'SFC'`.
7. Confirm one `met_em.d01.*.nc` file exists for every requested hour before running `real.exe`.

The ERA-interim pressure-level Vtable is used as the initial WPS 4.6 compatibility path because it contains the ECMWF pressure and surface parameter mappings. This handoff still requires an end-to-end ERA5/WPS acceptance test.
"""
    _write(instructions_path, instructions, force)

    manifest = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "package": "wrf-era5-case",
        "case": config.name,
        "start": config.start.isoformat(),
        "end": config.end.isoformat(),
        "domain": {
            "center": [config.ref_lat, config.ref_lon],
            "dimensions": [config.e_we, config.e_sn, config.e_vert],
            "spacing_metres": [config.dx, config.dy],
            "era5_area_nwse": era5_area(config),
        },
        "profiles": {"physics": config.physics_profile, "geodata": config.geography_profile},
        "inputs": {
            "geodata": str(geog_root),
            "era5_requests": [
                {"dataset": item.dataset, "target": str(item.target), "request": item.request}
                for item in requests
            ],
        },
        "configuration_sha256": hashlib.sha256(config.source.read_bytes()).hexdigest(),
        "limitations": [
            "The ERA5 rectangle is a conservative estimate, not an exact projection of WRF corners.",
            "The demonstration physics profile requires scientific review before research use.",
            "Generated namelists have not yet been validated by WPS or real.exe.",
        ],
    }
    _write(manifest_path, json.dumps(manifest, indent=2, sort_keys=True) + "\n", force)
    return {
        "namelist_wps": wps_path,
        "namelist_wps_pressure": wps_pressure_path,
        "namelist_wps_surface": wps_surface_path,
        "namelist_input": wrf_path,
        "configuration": config_copy,
        "physics_profile": profile_copy,
        "wps_steps": instructions_path,
        "manifest": manifest_path,
    }
