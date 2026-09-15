from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from pathlib import Path

from .config import CaseConfig
from .era5 import build_requests, is_grib
from .geodata import geodata_status


@dataclass(frozen=True)
class Check:
    status: str
    name: str
    detail: str


def _writable_target(path: Path) -> bool:
    current = path
    while not current.exists() and current != current.parent:
        current = current.parent
    return current.is_dir() and os.access(current, os.W_OK)


def run_checks(config: CaseConfig) -> list[Check]:
    checks: list[Check] = []
    credentials = Path.home() / ".cdsapirc"
    if credentials.is_file():
        checks.append(Check("PASS", "CDS credentials", f"found {credentials}"))
    else:
        checks.append(Check(
            "FAIL", "CDS credentials",
            "~/.cdsapirc was not found; configure CDS access at https://cds.climate.copernicus.eu/how-to-api",
        ))

    if importlib.util.find_spec("cdsapi"):
        checks.append(Check("PASS", "CDS client", "cdsapi is importable"))
    else:
        checks.append(Check("FAIL", "CDS client", "cdsapi is not installed; install this package first"))

    for label, path in (
        ("ERA5 directory", config.era5_directory),
        ("geodata directory", config.geography_directory),
        ("case directory", config.case_directory),
    ):
        status = "PASS" if _writable_target(path) else "FAIL"
        checks.append(Check(status, label, f"writable target: {path}" if status == "PASS" else f"not writable: {path}"))

    geography = geodata_status(config)
    if geography["installed"]:
        checks.append(Check("PASS", "WPS geodata", f"found {geography['geog_data_path']}"))
    else:
        checks.append(Check("INFO", "WPS geodata", f"not installed in {config.geography_directory}"))

    requests = build_requests(config)
    ready = sum(is_grib(item.target) for item in requests)
    checks.append(Check(
        "PASS" if ready == len(requests) else "INFO",
        "ERA5 files", f"{ready} of {len(requests)} daily GRIB files already available",
    ))
    return checks


def checks_pass(checks: list[Check]) -> bool:
    return not any(item.status == "FAIL" for item in checks)
