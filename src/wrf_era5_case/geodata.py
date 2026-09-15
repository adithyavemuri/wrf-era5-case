from __future__ import annotations

import json
import shutil
import tarfile
import urllib.request
from pathlib import Path

from .config import CaseConfig


GEODATA_URLS = {
    "low": "https://www2.mmm.ucar.edu/wrf/src/wps_files/geog_low_res_mandatory.tar.gz",
    "high": "https://www2.mmm.ucar.edu/wrf/src/wps_files/geog_high_res_mandatory.tar.gz",
}

GEODATA_COMPRESSED_BYTES = {
    "low": 149_872_777,
    "high": 2_772_782_816,
}

REQUIRED_DATASETS = ("albedo_modis", "soiltemp_1deg")


def find_geodata_root(directory: Path) -> Path | None:
    candidates = [directory]
    if directory.is_dir():
        candidates.extend(path for path in directory.iterdir() if path.is_dir())
    for candidate in candidates:
        if all((candidate / name / "index").is_file() for name in REQUIRED_DATASETS):
            return candidate.resolve()
    return None


def geodata_status(config: CaseConfig) -> dict[str, object]:
    root = find_geodata_root(config.geography_directory)
    return {
        "profile": config.geography_profile,
        "configured_directory": str(config.geography_directory),
        "installed": root is not None,
        "geog_data_path": str(root) if root else None,
        "url": GEODATA_URLS[config.geography_profile],
        "approximate_compressed_bytes": GEODATA_COMPRESSED_BYTES[config.geography_profile],
    }


def _safe_extract(archive: Path, destination: Path) -> None:
    root = destination.resolve()
    with tarfile.open(archive, "r:gz") as handle:
        for member in handle.getmembers():
            target = (destination / member.name).resolve()
            if target != root and root not in target.parents:
                raise RuntimeError(f"unsafe path in geodata archive: {member.name}")
            if member.issym() or member.islnk() or member.isdev():
                raise RuntimeError(f"unsupported special entry in geodata archive: {member.name}")
        handle.extractall(destination)


def download_geodata(config: CaseConfig, *, force: bool = False) -> Path:
    existing = find_geodata_root(config.geography_directory)
    if existing and not force:
        return existing
    config.geography_directory.mkdir(parents=True, exist_ok=True)
    url = GEODATA_URLS[config.geography_profile]
    archive = config.geography_directory / Path(url).name
    temporary = archive.with_suffix(archive.suffix + ".part")
    if force:
        archive.unlink(missing_ok=True)
        temporary.unlink(missing_ok=True)
    if not archive.exists():
        offset = temporary.stat().st_size if temporary.exists() else 0
        request = urllib.request.Request(url)
        if offset:
            request.add_header("Range", f"bytes={offset}-")
        with urllib.request.urlopen(request) as response:
            resumed = offset > 0 and getattr(response, "status", None) == 206
            mode = "ab" if resumed else "wb"
            with temporary.open(mode) as output:
                shutil.copyfileobj(response, output, length=1024 * 1024)
        temporary.replace(archive)
    if not tarfile.is_tarfile(archive):
        raise RuntimeError(f"download is not a valid tar archive: {archive}")
    _safe_extract(archive, config.geography_directory)
    root = find_geodata_root(config.geography_directory)
    if root is None:
        raise RuntimeError("geodata archive extracted but mandatory index files were not found")
    marker = config.geography_directory / ".wrf-era5-case-geodata.json"
    marker.write_text(json.dumps({"profile": config.geography_profile, "url": url, "root": str(root)}, indent=2) + "\n")
    return root
