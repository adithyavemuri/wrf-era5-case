from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib


class ConfigurationError(ValueError):
    """Raised when a case configuration is incomplete or unsafe."""


DEFAULT_PRESSURE_LEVELS = (
    1000, 975, 950, 925, 900, 875, 850, 825, 800, 775, 750, 700, 650,
    600, 550, 500, 450, 400, 350, 300, 250, 225, 200, 175, 150, 125,
    100, 70, 50, 30, 20, 10, 7, 5, 3, 2, 1,
)

NAMELIST_DEFAULTS: dict[str, dict[str, int | float | bool]] = {
    "time_control": {
        "history_interval": 60,
        "adjust_output_times": True,
        "frames_per_outfile": 1,
        "restart": False,
        "restart_interval": 180,
        "io_form_history": 2,
        "io_form_restart": 2,
        "io_form_input": 2,
        "io_form_boundary": 2,
    },
    "domains": {
        "time_step": 54,
        "p_top_requested": 5000,
        "feedback": 0,
        "smooth_option": 0,
    },
    "physics": {
        "mp_physics": 4,
        "ra_lw_physics": 4,
        "ra_sw_physics": 4,
        "radt": 9,
        "sf_sfclay_physics": 1,
        "sf_surface_physics": 2,
        "bl_pbl_physics": 1,
        "bldt": 0,
        "cu_physics": 1,
        "cudt": 5,
        "isfflx": 1,
        "ifsnow": 1,
        "icloud": 1,
        "surface_input_source": 1,
        "num_soil_layers": 4,
        "sf_urban_physics": 0,
        "maxiens": 1,
        "maxens": 3,
        "maxens2": 3,
        "maxens3": 16,
        "ensdim": 144,
    },
    "dynamics": {
        "w_damping": 0,
        "diff_opt": 1,
        "km_opt": 4,
        "diff_6th_opt": 0,
        "diff_6th_factor": 0.12,
        "base_temp": 290.0,
        "damp_opt": 0,
        "zdamp": 5000.0,
        "dampcoef": 0.2,
        "khdif": 0,
        "kvdif": 0,
        "non_hydrostatic": True,
        "moist_adv_opt": 1,
        "scalar_adv_opt": 1,
    },
}


@dataclass(frozen=True)
class DomainConfig:
    name: str
    domain_id: int
    parent_id: int
    parent_grid_ratio: int
    parent_time_step_ratio: int
    i_parent_start: int
    j_parent_start: int
    e_we: int
    e_sn: int
    e_vert: int
    dx: float
    dy: float


@dataclass(frozen=True)
class CaseConfig:
    source: Path
    name: str
    start: datetime
    end: datetime
    interval_seconds: int
    ref_lat: float
    ref_lon: float
    truelat1: float
    truelat2: float
    stand_lon: float
    map_projection: str
    dx: float
    dy: float
    e_we: int
    e_sn: int
    e_vert: int
    domains: tuple[DomainConfig, ...]
    margin_degrees: float
    pressure_levels: tuple[int, ...]
    forcing_mode: str
    era5_directory: Path
    geography_profile: str
    geography_directory: Path
    physics_profile: str
    history_interval_minutes: int
    time_step_seconds: int
    namelist_options: dict[str, dict[str, int | float | bool]]
    eta_levels: tuple[float, ...] | None
    case_directory: Path

    @property
    def duration_seconds(self) -> int:
        return int((self.end - self.start).total_seconds())


def _section(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name)
    if not isinstance(value, dict):
        raise ConfigurationError(f"missing [{name}] section")
    return value


def _required(section: dict[str, Any], key: str, section_name: str) -> Any:
    if key not in section:
        raise ConfigurationError(f"missing {section_name}.{key}")
    return section[key]


def _datetime(value: Any, field: str) -> datetime:
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, str):
        try:
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ConfigurationError(f"{field} must be an ISO date/time") from exc
    else:
        raise ConfigurationError(f"{field} must be an ISO date/time string")
    if result.tzinfo is not None:
        result = result.astimezone(timezone.utc).replace(tzinfo=None)
    return result


def _path(value: Any, base: Path) -> Path:
    candidate = Path(str(value)).expanduser()
    return candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve()


def _domains(data: dict[str, Any]) -> tuple[dict[str, Any], tuple[DomainConfig, ...]]:
    raw = data.get("domain")
    if isinstance(raw, dict):
        tables = [raw]
    elif isinstance(raw, list) and raw and all(isinstance(item, dict) for item in raw):
        tables = raw
    else:
        raise ConfigurationError("missing [domain] or [[domain]] section")
    outer = tables[0]
    domains: list[DomainConfig] = []
    names: set[str] = set()
    for index, table in enumerate(tables, 1):
        name = str(table.get("name", f"d{index:02d}"))
        if name in names:
            raise ConfigurationError(f"duplicate domain name: {name}")
        names.add(name)
        ratio = int(table.get("parent_grid_ratio", 1 if index == 1 else 3))
        parent_id = int(table.get("parent_id", 1))
        parent = domains[parent_id - 1] if index > 1 and 1 <= parent_id < index else None
        if index > 1 and parent is None:
            raise ConfigurationError(f"domain {name} must reference an earlier parent_id")
        dx = float(table["dx"] if "dx" in table else parent.dx / ratio if parent else _required(table, "dx", "domain"))
        dy = float(table["dy"] if "dy" in table else parent.dy / ratio if parent else _required(table, "dy", "domain"))
        domains.append(DomainConfig(
            name=name, domain_id=index, parent_id=parent_id,
            parent_grid_ratio=ratio,
            parent_time_step_ratio=int(table.get("parent_time_step_ratio", ratio)),
            i_parent_start=int(table.get("i_parent_start", 1)),
            j_parent_start=int(table.get("j_parent_start", 1)),
            e_we=int(_required(table, "nx", "domain")),
            e_sn=int(_required(table, "ny", "domain")),
            e_vert=int(table.get("vertical_levels", outer.get("vertical_levels", 40))),
            dx=dx, dy=dy,
        ))
    return outer, tuple(domains)


def _namelist_options(data: dict[str, Any], wrf: dict[str, Any]) -> dict[str, dict[str, int | float | bool]]:
    raw = data.get("namelist", {})
    if not isinstance(raw, dict):
        raise ConfigurationError("[namelist] must be a TOML table")
    unknown_groups = set(raw) - set(NAMELIST_DEFAULTS)
    if unknown_groups:
        raise ConfigurationError(f"unsupported namelist groups: {sorted(unknown_groups)}")

    result = {group: dict(defaults) for group, defaults in NAMELIST_DEFAULTS.items()}
    result["time_control"]["history_interval"] = int(wrf.get("history_interval_minutes", 60))
    result["domains"]["time_step"] = int(wrf.get("time_step_seconds", 54))
    for group, defaults in NAMELIST_DEFAULTS.items():
        overrides = raw.get(group, {})
        if not isinstance(overrides, dict):
            raise ConfigurationError(f"[namelist.{group}] must be a TOML table")
        unknown = set(overrides) - set(defaults)
        if unknown:
            raise ConfigurationError(
                f"unsupported keys in [namelist.{group}]: {sorted(unknown)}"
            )
        for key, value in overrides.items():
            expected = defaults[key]
            if isinstance(expected, bool):
                valid = isinstance(value, bool)
            elif isinstance(expected, int):
                valid = isinstance(value, int) and not isinstance(value, bool)
            else:
                valid = isinstance(value, (int, float)) and not isinstance(value, bool)
            if not valid:
                raise ConfigurationError(
                    f"namelist.{group}.{key} must be a {type(expected).__name__}"
                )
            result[group][key] = value
    return result


def load_config(path: str | Path) -> CaseConfig:
    source = Path(path).expanduser().resolve()
    try:
        with source.open("rb") as handle:
            data = tomllib.load(handle)
    except FileNotFoundError as exc:
        raise ConfigurationError(f"configuration file not found: {source}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigurationError(f"invalid TOML in {source}: {exc}") from exc

    case = _section(data, "case")
    domain, domains = _domains(data)
    era5 = _section(data, "era5")
    geodata = _section(data, "geodata")
    wrf = _section(data, "wrf")
    output = _section(data, "output")
    base = source.parent
    namelist_options = _namelist_options(data, wrf)
    restart = data.get("restart", {})
    if not isinstance(restart, dict):
        raise ConfigurationError("[restart] must be a TOML table")
    finest_spacing = min(min(item.dx, item.dy) for item in domains)
    automatic_restart = 60 if finest_spacing <= 500 else 120 if finest_spacing <= 1000 else 180
    restart_enabled = restart.get("enabled", True)
    if not isinstance(restart_enabled, bool):
        raise ConfigurationError("restart.enabled must be a boolean")
    namelist_options["time_control"]["restart"] = False
    namelist_options["time_control"]["restart_interval"] = int(
        restart.get("interval_minutes", automatic_restart)
        if restart_enabled else int(((_datetime(_required(case, "end", "case"), "case.end") - _datetime(_required(case, "start", "case"), "case.start")).total_seconds() // 60) + 1)
    )
    vertical_grid = data.get("vertical_grid", {})
    if not isinstance(vertical_grid, dict):
        raise ConfigurationError("[vertical_grid] must be a TOML table")
    raw_eta = vertical_grid.get("eta_levels")
    eta_levels = tuple(float(value) for value in raw_eta) if isinstance(raw_eta, list) else None
    if raw_eta is not None and not isinstance(raw_eta, list):
        raise ConfigurationError("vertical_grid.eta_levels must be a TOML array")

    config = CaseConfig(
        source=source,
        name=str(_required(case, "name", "case")).strip(),
        start=_datetime(_required(case, "start", "case"), "case.start"),
        end=_datetime(_required(case, "end", "case"), "case.end"),
        interval_seconds=int(case.get("interval_seconds", 3600)),
        ref_lat=float(_required(domain, "center_latitude", "domain")),
        ref_lon=float(_required(domain, "center_longitude", "domain")),
        truelat1=float(domain.get("true_latitude_1", domain["center_latitude"])),
        truelat2=float(domain.get("true_latitude_2", domain["center_latitude"])),
        stand_lon=float(domain.get("standard_longitude", domain["center_longitude"])),
        map_projection=str(domain.get("map_projection", "lambert")).lower(),
        dx=float(_required(domain, "dx", "domain")),
        dy=float(_required(domain, "dy", "domain")),
        e_we=int(_required(domain, "nx", "domain")),
        e_sn=int(_required(domain, "ny", "domain")),
        e_vert=int(domain.get("vertical_levels", 40)),
        domains=domains,
        margin_degrees=float(era5.get("margin_degrees", 1.0)),
        pressure_levels=tuple(int(value) for value in era5.get("pressure_levels", DEFAULT_PRESSURE_LEVELS)),
        forcing_mode=str(era5.get("forcing_mode", "reanalysis")).lower(),
        era5_directory=_path(era5.get("directory", "data/ERA5"), base),
        geography_profile=str(geodata.get("profile", "low")).lower(),
        geography_directory=_path(geodata.get("directory", "data/WPS_GEOG"), base),
        physics_profile=str(wrf.get("physics_profile", "demonstration")),
        history_interval_minutes=int(namelist_options["time_control"]["history_interval"]),
        time_step_seconds=int(namelist_options["domains"]["time_step"]),
        namelist_options=namelist_options,
        eta_levels=eta_levels,
        case_directory=_path(output.get("case_directory", f"cases/{case.get('name', 'case')}"), base),
    )
    validate_config(config)
    return config


def validate_config(config: CaseConfig) -> None:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", config.name) or config.name in {".", ".."}:
        raise ConfigurationError("case.name must contain only letters, numbers, '.', '_' and '-'")
    if config.end <= config.start:
        raise ConfigurationError("case.end must be later than case.start")
    if config.start.minute or config.start.second or config.end.minute or config.end.second:
        raise ConfigurationError("ERA5 demonstration cases must start and end on complete hours")
    if config.interval_seconds != 3600:
        raise ConfigurationError("version 0.2 supports hourly ERA5 input (interval_seconds=3600) only")
    if not -90 <= config.ref_lat <= 90 or not -180 <= config.ref_lon <= 180:
        raise ConfigurationError("domain centre must be valid latitude/longitude")
    if config.map_projection not in {"lambert", "mercator"}:
        raise ConfigurationError("domain.map_projection must currently be 'lambert' or 'mercator'")
    if config.dx <= 0 or config.dy <= 0 or config.e_we < 10 or config.e_sn < 10:
        raise ConfigurationError("domain spacing must be positive and nx/ny must each be at least 10")
    if config.e_vert < 10:
        raise ConfigurationError("domain.vertical_levels must be at least 10")
    for domain in config.domains:
        if domain.dx <= 0 or domain.dy <= 0 or domain.e_we < 10 or domain.e_sn < 10 or domain.e_vert < 10:
            raise ConfigurationError(f"domain {domain.name} has invalid spacing or dimensions")
        if domain.domain_id == 1:
            if domain.parent_id != 1 or domain.parent_grid_ratio != 1:
                raise ConfigurationError("the outer domain must have parent_id=1 and parent_grid_ratio=1")
            continue
        parent = config.domains[domain.parent_id - 1]
        ratio = domain.parent_grid_ratio
        if ratio < 2 or domain.parent_time_step_ratio < 1:
            raise ConfigurationError(f"domain {domain.name} requires parent_grid_ratio >= 2")
        if (domain.e_we - 1) % ratio or (domain.e_sn - 1) % ratio:
            raise ConfigurationError(f"domain {domain.name} nx-1 and ny-1 must be divisible by parent_grid_ratio")
        if domain.i_parent_start < 1 or domain.j_parent_start < 1:
            raise ConfigurationError(f"domain {domain.name} parent starts must be positive")
        if domain.i_parent_start + (domain.e_we - 1) // ratio > parent.e_we or domain.j_parent_start + (domain.e_sn - 1) // ratio > parent.e_sn:
            raise ConfigurationError(f"domain {domain.name} does not fit inside its parent")
        if abs(domain.dx * ratio - parent.dx) > 1e-6 or abs(domain.dy * ratio - parent.dy) > 1e-6:
            raise ConfigurationError(f"domain {domain.name} spacing does not match its parent_grid_ratio")
    if config.history_interval_minutes <= 0:
        raise ConfigurationError("namelist.time_control.history_interval must be positive")
    if config.time_step_seconds <= 0:
        raise ConfigurationError("namelist.domains.time_step must be positive")
    if config.namelist_options["domains"]["feedback"] != 0:
        raise ConfigurationError("only stationary one-way nesting is supported; namelist.domains.feedback must be 0")
    if int(config.namelist_options["time_control"]["restart_interval"]) <= 0:
        raise ConfigurationError("restart.interval_minutes must be positive")
    if config.eta_levels is not None:
        if len(config.eta_levels) < 10:
            raise ConfigurationError("vertical_grid.eta_levels must contain at least 10 full levels")
        if abs(config.eta_levels[0] - 1.0) > 1e-9 or abs(config.eta_levels[-1]) > 1e-9:
            raise ConfigurationError("vertical_grid.eta_levels must start at 1.0 and end at 0.0")
        if any(upper <= lower for upper, lower in zip(config.eta_levels, config.eta_levels[1:])):
            raise ConfigurationError("vertical_grid.eta_levels must be strictly decreasing")
        if any(domain.e_vert != len(config.eta_levels) for domain in config.domains):
            raise ConfigurationError("every domain.vertical_levels must equal the number of custom eta_levels")
    if config.margin_degrees < 0:
        raise ConfigurationError("era5.margin_degrees cannot be negative")
    if config.forcing_mode != "reanalysis":
        raise ConfigurationError("version 0.2 supports era5.forcing_mode='reanalysis' only")
    if config.geography_profile not in {"low", "high"}:
        raise ConfigurationError("geodata.profile must be 'low' or 'high'")
    if config.physics_profile != "demonstration":
        raise ConfigurationError("version 0.2 supports wrf.physics_profile='demonstration' only")
    if not config.pressure_levels:
        raise ConfigurationError("era5.pressure_levels cannot be empty")
    if len(config.pressure_levels) != len(set(config.pressure_levels)):
        raise ConfigurationError("era5.pressure_levels cannot contain duplicates")
    if tuple(sorted(config.pressure_levels, reverse=True)) != config.pressure_levels:
        raise ConfigurationError("era5.pressure_levels must be ordered from highest pressure to lowest")
    unknown = set(config.pressure_levels) - set(DEFAULT_PRESSURE_LEVELS)
    if unknown:
        raise ConfigurationError(f"unsupported ERA5 pressure levels: {sorted(unknown)}")
