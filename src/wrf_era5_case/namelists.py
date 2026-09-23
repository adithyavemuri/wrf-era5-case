from __future__ import annotations

import hashlib
import json
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


def _fortran_value(value: int | float | bool) -> str:
    if isinstance(value, bool):
        return ".true." if value else ".false."
    if isinstance(value, float):
        return repr(value)
    return str(value)


def _namelist_lines(
    options: dict[str, int | float | bool], *, count: int = 1, repeated: set[str] | None = None
) -> str:
    repeated = repeated or set()
    return "\n".join(
        f" {name:<35} = {', '.join([_fortran_value(value)] * count) if name in repeated else _fortran_value(value)},"
        for name, value in options.items()
    )


def _effective_namelist_markdown(config: CaseConfig) -> str:
    sections = ["\n## Effective TOML-controlled namelist values\n"]
    for group, options in config.namelist_options.items():
        sections.append(f"### `&{group}`\n")
        sections.append("| Key | Effective value |\n|---|---|\n")
        sections.extend(f"| `{key}` | `{_fortran_value(value)}` |\n" for key, value in options.items())
        sections.append("\n")
    return "".join(sections)


def _case_contents(config: CaseConfig, requests: list[Era5Request]) -> tuple[dict[str, Path], dict[Path, str]]:
    destination = config.case_directory
    geog_root = find_geodata_root(config.geography_directory) or config.geography_directory
    domains = config.domains
    csv = lambda values: ", ".join(str(value) for value in values)
    quoted = lambda values: ", ".join(f"'{value}'" for value in values)
    repeated = lambda value: [value] * len(domains)
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
        "MAP_PROJECTION": config.map_projection,
        "GEOG_DATA_PATH": str(geog_root),
        "GEOG_DATA_RES": "lowres" if config.geography_profile == "low" else "default",
        "MAX_DOM": len(domains),
        "START_DATES": quoted(repeated(_wps_date(config.start))),
        "END_DATES": quoted(repeated(_wps_date(config.end))),
        "PARENT_IDS": csv(domain.parent_id for domain in domains),
        "PARENT_GRID_RATIOS": csv(domain.parent_grid_ratio for domain in domains),
        "PARENT_TIME_STEP_RATIOS": csv(domain.parent_time_step_ratio for domain in domains),
        "I_PARENT_STARTS": csv(domain.i_parent_start for domain in domains),
        "J_PARENT_STARTS": csv(domain.j_parent_start for domain in domains),
        "E_WES": csv(domain.e_we for domain in domains),
        "E_SNS": csv(domain.e_sn for domain in domains),
        "E_VERTS": csv(domain.e_vert for domain in domains),
        "DXS": csv(f"{domain.dx:g}" for domain in domains),
        "DYS": csv(f"{domain.dy:g}" for domain in domains),
        "GRID_IDS": csv(domain.domain_id for domain in domains),
        "GEOG_DATA_RESOLUTIONS": quoted(repeated("lowres" if config.geography_profile == "low" else "default")),
    }
    days, hours, minutes, seconds = _duration_values(config)
    wrf_values = dict(shared)
    time_arrays = {"history_interval", "frames_per_outfile"}
    physics_scalars = {"isfflx", "ifsnow", "icloud", "surface_input_source", "num_soil_layers", "maxiens", "maxens", "maxens2", "maxens3", "ensdim"}
    physics_arrays = set(config.namelist_options["physics"]) - physics_scalars
    dynamics_arrays = set(config.namelist_options["dynamics"]) - {"w_damping", "base_temp", "damp_opt"}
    wrf_values.update({
        "RUN_DAYS": days,
        "RUN_HOURS": hours,
        "RUN_MINUTES": minutes,
        "RUN_SECONDS": seconds,
        "START_YEARS": csv(repeated(config.start.year)),
        "START_MONTHS": csv(repeated(config.start.month)),
        "START_DAYS": csv(repeated(config.start.day)),
        "START_HOURS": csv(repeated(config.start.hour)),
        "END_YEARS": csv(repeated(config.end.year)),
        "END_MONTHS": csv(repeated(config.end.month)),
        "END_DAYS": csv(repeated(config.end.day)),
        "END_HOURS": csv(repeated(config.end.hour)),
        "SPECIFIED": csv([".true."] + [".false."] * (len(domains) - 1)),
        "NESTED": csv([".false."] + [".true."] * (len(domains) - 1)),
        "NUM_METGRID_LEVELS": len(config.pressure_levels) + 1,
        "INPUT_FROM_FILE": csv(repeated(".true.")),
        "VERTICAL_GRID_OPTIONS": (
            " eta_levels                          = "
            + csv(f"{value:.8g}" for value in config.eta_levels)
            + ","
            if config.eta_levels is not None else ""
        ),
        "TIME_CONTROL_OPTIONS": _namelist_lines(config.namelist_options["time_control"], count=len(domains), repeated=time_arrays),
        "DOMAIN_OPTIONS": _namelist_lines(config.namelist_options["domains"]),
        "PHYSICS_OPTIONS": _namelist_lines(config.namelist_options["physics"], count=len(domains), repeated=physics_arrays),
        "DYNAMICS_OPTIONS": _namelist_lines(config.namelist_options["dynamics"], count=len(domains), repeated=dynamics_arrays),
    })

    wps_path = destination / "namelist.wps"
    wrf_path = destination / "namelist.input"
    config_copy = destination / "case.toml"
    profile_copy = destination / "PHYSICS_PROFILE.md"
    manifest_path = destination / "case-manifest.json"
    instructions_path = destination / "WPS_STEPS.md"
    wps = _render("namelist.wps.template", shared)
    profile_text = files("wrf_era5_case").joinpath("templates", "demonstration", "README.md").read_text()
    profile_text += _effective_namelist_markdown(config)
    instructions = f"""# WPS handoff for {config.name}

This package prepares the case but does not run WPS in version 0.2.

1. Use `namelist.wps` to run `geogrid.exe`.
2. Link WPS `Vtable.ECMWF` as `Vtable`.
3. Link both the ERA5 pressure-level and single-level GRIB files into the same WPS working directory.
4. Run `ungrib.exe` once to create the combined `ERA5:*` intermediate files.
5. Run `metgrid.exe`; `namelist.wps` declares `fg_name = 'ERA5'`.
6. Confirm one `met_em.d01.*.nc` file exists for every requested hour before running `real.exe`.

This combined-input route uses the current ECMWF table shipped with WPS. Every newly generated case still requires its own WPS and `real.exe` validation.
"""
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
            "domains": [domain.__dict__ for domain in domains],
        },
        "profiles": {
            "forcing": f"ERA5 {config.forcing_mode}",
            "physics": config.physics_profile,
            "geodata": config.geography_profile,
        },
        "effective_namelist": config.namelist_options,
        "inputs": {
            "geodata": str(geog_root),
            "era5_requests": [
                {"dataset": item.dataset, "target": str(item.target), "request": item.request}
                for item in requests
            ],
        },
        "configuration_sha256": hashlib.sha256(config.source.read_bytes()).hexdigest(),
        "limitations": [
            "This is a WRF simulation forced by ERA5 reanalysis, not a newly produced reanalysis.",
            "The ERA5 rectangle is a conservative estimate, not an exact projection of WRF corners.",
            "The demonstration physics profile requires scientific review before research use.",
            "Validation status is not inferred; run WPS and real.exe for this generated case.",
        ],
    }
    paths = {
        "namelist_wps": wps_path,
        "namelist_input": wrf_path,
        "configuration": config_copy,
        "physics_profile": profile_copy,
        "wps_steps": instructions_path,
        "manifest": manifest_path,
    }
    contents = {
        wps_path: wps,
        wrf_path: _render("namelist.input.template", wrf_values),
        profile_copy: profile_text,
        instructions_path: instructions,
        manifest_path: json.dumps(manifest, indent=2, sort_keys=True) + "\n",
    }
    if config.source != config_copy:
        contents[config_copy] = config.source.read_text()
    return paths, contents


def _manifest_equivalent(existing: str, desired: str) -> bool:
    try:
        existing_data = json.loads(existing)
        desired_data = json.loads(desired)
    except json.JSONDecodeError:
        return False
    existing_data.pop("created_utc", None)
    desired_data.pop("created_utc", None)
    return existing_data == desired_data


def configuration_conflicts(config: CaseConfig, requests: list[Era5Request]) -> list[Path]:
    paths, contents = _case_contents(config, requests)
    manifest_path = paths["manifest"]
    conflicts: list[Path] = []
    for path, desired in contents.items():
        if not path.exists():
            continue
        existing = path.read_text()
        equivalent = _manifest_equivalent(existing, desired) if path == manifest_path else existing == desired
        if not equivalent:
            conflicts.append(path)
    return conflicts


def require_writable_configuration(
    config: CaseConfig, requests: list[Era5Request], *, force: bool = False
) -> None:
    conflicts = configuration_conflicts(config, requests)
    if conflicts and not force:
        names = ", ".join(str(path) for path in conflicts)
        raise RuntimeError(
            "generated case files differ from the requested configuration: "
            f"{names}. Review them, then use 'configure --force' or 'prepare --force-config' "
            "to replace only generated case configuration files"
        )


def configure_case(config: CaseConfig, requests: list[Era5Request], *, force: bool = False) -> dict[str, Path]:
    config.case_directory.mkdir(parents=True, exist_ok=True)
    paths, contents = _case_contents(config, requests)
    require_writable_configuration(config, requests, force=force)
    manifest_path = paths["manifest"]
    for path, desired in contents.items():
        if path.exists() and not force:
            existing = path.read_text()
            equivalent = _manifest_equivalent(existing, desired) if path == manifest_path else existing == desired
            if equivalent:
                continue
        path.write_text(desired)
    return paths
