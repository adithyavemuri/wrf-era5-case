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
    dx: float
    dy: float
    e_we: int
    e_sn: int
    e_vert: int
    margin_degrees: float
    pressure_levels: tuple[int, ...]
    forcing_mode: str
    era5_directory: Path
    geography_profile: str
    geography_directory: Path
    physics_profile: str
    history_interval_minutes: int
    time_step_seconds: int
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
    domain = _section(data, "domain")
    era5 = _section(data, "era5")
    geodata = _section(data, "geodata")
    wrf = _section(data, "wrf")
    output = _section(data, "output")
    base = source.parent

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
        dx=float(_required(domain, "dx", "domain")),
        dy=float(_required(domain, "dy", "domain")),
        e_we=int(_required(domain, "nx", "domain")),
        e_sn=int(_required(domain, "ny", "domain")),
        e_vert=int(domain.get("vertical_levels", 40)),
        margin_degrees=float(era5.get("margin_degrees", 1.0)),
        pressure_levels=tuple(int(value) for value in era5.get("pressure_levels", DEFAULT_PRESSURE_LEVELS)),
        forcing_mode=str(era5.get("forcing_mode", "reanalysis")).lower(),
        era5_directory=_path(era5.get("directory", "data/ERA5"), base),
        geography_profile=str(geodata.get("profile", "low")).lower(),
        geography_directory=_path(geodata.get("directory", "data/WPS_GEOG"), base),
        physics_profile=str(wrf.get("physics_profile", "demonstration")),
        history_interval_minutes=int(wrf.get("history_interval_minutes", 60)),
        time_step_seconds=int(wrf.get("time_step_seconds", 54)),
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
        raise ConfigurationError("version 0.1 supports hourly ERA5 input (interval_seconds=3600) only")
    if not -90 <= config.ref_lat <= 90 or not -180 <= config.ref_lon <= 180:
        raise ConfigurationError("domain centre must be valid latitude/longitude")
    if config.dx <= 0 or config.dy <= 0 or config.e_we < 10 or config.e_sn < 10:
        raise ConfigurationError("domain spacing must be positive and nx/ny must each be at least 10")
    if config.e_vert < 10:
        raise ConfigurationError("domain.vertical_levels must be at least 10")
    if config.margin_degrees < 0:
        raise ConfigurationError("era5.margin_degrees cannot be negative")
    if config.forcing_mode != "reanalysis":
        raise ConfigurationError("version 0.1 supports era5.forcing_mode='reanalysis' only")
    if config.geography_profile not in {"low", "high"}:
        raise ConfigurationError("geodata.profile must be 'low' or 'high'")
    if config.physics_profile != "demonstration":
        raise ConfigurationError("version 0.1 supports wrf.physics_profile='demonstration' only")
    if not config.pressure_levels:
        raise ConfigurationError("era5.pressure_levels cannot be empty")
    if len(config.pressure_levels) != len(set(config.pressure_levels)):
        raise ConfigurationError("era5.pressure_levels cannot contain duplicates")
    if tuple(sorted(config.pressure_levels, reverse=True)) != config.pressure_levels:
        raise ConfigurationError("era5.pressure_levels must be ordered from highest pressure to lowest")
    unknown = set(config.pressure_levels) - set(DEFAULT_PRESSURE_LEVELS)
    if unknown:
        raise ConfigurationError(f"unsupported ERA5 pressure levels: {sorted(unknown)}")
