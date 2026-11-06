from __future__ import annotations

import json
import hashlib
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from .config import CaseConfig
from .domain import era5_area


PRESSURE_DATASET = "reanalysis-era5-pressure-levels"
SINGLE_DATASET = "reanalysis-era5-single-levels"

PRESSURE_VARIABLES = (
    "geopotential",
    "relative_humidity",
    "temperature",
    "u_component_of_wind",
    "v_component_of_wind",
)

SINGLE_VARIABLES = (
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "2m_dewpoint_temperature",
    "2m_temperature",
    "geopotential",
    "land_sea_mask",
    "mean_sea_level_pressure",
    "sea_ice_cover",
    "sea_surface_temperature",
    "skin_temperature",
    "snow_depth",
    "soil_temperature_level_1",
    "soil_temperature_level_2",
    "soil_temperature_level_3",
    "soil_temperature_level_4",
    "surface_pressure",
    "volumetric_soil_water_layer_1",
    "volumetric_soil_water_layer_2",
    "volumetric_soil_water_layer_3",
    "volumetric_soil_water_layer_4",
)


@dataclass(frozen=True)
class Era5Request:
    family: str
    dataset: str
    request: dict[str, Any]
    target: Path


def requested_times(config: CaseConfig) -> list[datetime]:
    values: list[datetime] = []
    current = config.start
    while current <= config.end:
        values.append(current)
        current += timedelta(seconds=config.interval_seconds)
    return values


def build_requests(config: CaseConfig) -> list[Era5Request]:
    by_day: dict[str, list[str]] = {}
    for value in requested_times(config):
        by_day.setdefault(value.strftime("%Y-%m-%d"), []).append(value.strftime("%H:%M"))

    north, west, south, east = era5_area(config)
    # ERA5 CDS regular grids are 0.25 degrees; round OUTWARD, never shrink
    # the requested coverage by rounding a geographic boundary inward.
    area = [math.ceil(north*4)/4, math.floor(west*4)/4,
            math.floor(south*4)/4, math.ceil(east*4)/4]
    requests: list[Era5Request] = []
    for day, times in by_day.items():
        stamp = day.replace("-", "")
        shared: dict[str, Any] = {
            "product_type": ["reanalysis"],
            "year": [day[0:4]],
            "month": [day[5:7]],
            "day": [day[8:10]],
            "time": times,
            "area": area,
            "data_format": "grib",
            "download_format": "unarchived",
        }
        pressure = dict(shared)
        pressure["variable"] = list(PRESSURE_VARIABLES)
        pressure["pressure_level"] = [str(value) for value in config.pressure_levels]
        single = dict(shared)
        single["variable"] = list(SINGLE_VARIABLES)
        pressure_key = hashlib.sha256(json.dumps(pressure, sort_keys=True).encode()).hexdigest()[:16]
        single_key = hashlib.sha256(json.dumps(single, sort_keys=True).encode()).hexdigest()[:16]
        requests.append(Era5Request(
            "pressure-levels", PRESSURE_DATASET, pressure,
            config.era5_directory / f"era5-pressure-levels-{stamp}-{pressure_key}.grib",
        ))
        requests.append(Era5Request(
            "single-levels", SINGLE_DATASET, single,
            config.era5_directory / f"era5-single-levels-{stamp}-{single_key}.grib",
        ))
    return requests


def is_grib(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 16:
        return False
    with path.open("rb") as handle:
        return handle.read(4) == b"GRIB"


def write_request_files(config: CaseConfig, requests: list[Era5Request]) -> list[Path]:
    destination = config.case_directory / "requests"
    destination.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for item in requests:
        path = destination / f"{item.target.stem}.request.json"
        payload = {"dataset": item.dataset, "request": item.request, "target": str(item.target)}
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        paths.append(path)
    return paths


def download_requests(
    requests: list[Era5Request],
    *,
    force: bool = False,
    client_factory: Callable[[], Any] | None = None,
) -> tuple[list[Path], list[Path]]:
    from .grib_cache import cached_records, materialize, required

    downloaded: list[Path] = []
    reused: list[Path] = []
    client = None
    for item in requests:
        needs_download = force or not cached_records(item).keys() >= required(item.request)
        if needs_download and client is None:
            if client_factory is None:
                try:
                    import cdsapi
                except ModuleNotFoundError as exc:
                    raise RuntimeError("Install cdsapi before downloading ERA5") from exc
                client_factory = cdsapi.Client
            client = client_factory()
        changed = materialize(item, force=force, client=client)
        (downloaded if changed else reused).append(item.target)
    return downloaded, reused
