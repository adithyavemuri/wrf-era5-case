from __future__ import annotations

import json
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

    area = list(era5_area(config))
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
        requests.append(Era5Request(
            "pressure-levels", PRESSURE_DATASET, pressure,
            config.era5_directory / f"era5-pressure-levels-{stamp}.grib",
        ))
        single = dict(shared)
        single["variable"] = list(SINGLE_VARIABLES)
        requests.append(Era5Request(
            "single-levels", SINGLE_DATASET, single,
            config.era5_directory / f"era5-single-levels-{stamp}.grib",
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
    pending: list[Era5Request] = []
    reused: list[Path] = []
    for item in requests:
        if is_grib(item.target) and not force:
            reused.append(item.target)
            continue
        if item.target.exists() and not force:
            raise RuntimeError(f"existing file is not a recognizable GRIB file: {item.target}")
        pending.append(item)

    # cdsapi.Client may contact CDS while it initializes. Do not construct it
    # when every requested file can be reused locally.
    if not pending:
        return [], reused

    if client_factory is None:
        try:
            import cdsapi
        except ModuleNotFoundError as exc:
            raise RuntimeError("cdsapi is not installed; install the package before downloading") from exc
        client_factory = cdsapi.Client

    client = client_factory()
    downloaded: list[Path] = []
    for item in pending:
        item.target.parent.mkdir(parents=True, exist_ok=True)
        temporary = item.target.with_suffix(item.target.suffix + ".part")
        if temporary.exists():
            temporary.unlink()
        client.retrieve(item.dataset, item.request, str(temporary))
        if not is_grib(temporary):
            raise RuntimeError(f"CDS response is not a recognizable GRIB file: {temporary}")
        temporary.replace(item.target)
        downloaded.append(item.target)
    return downloaded, reused
