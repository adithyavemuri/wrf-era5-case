from __future__ import annotations

import io
import tarfile

import pytest

from conftest import write_config
from wrf_era5_case.config import load_config
from wrf_era5_case.geodata import _safe_extract, find_geodata_root, geodata_status


def test_finds_nested_geodata_root(tmp_path):
    config = load_config(write_config(tmp_path))
    root = config.geography_directory / "WPS_GEOG_LOW_RES"
    for name in ("albedo_modis", "soiltemp_1deg"):
        directory = root / name
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "index").write_text("test")
    assert find_geodata_root(config.geography_directory) == root.resolve()
    assert geodata_status(config)["installed"] is True


def test_rejects_archive_path_traversal(tmp_path):
    archive = tmp_path / "unsafe.tar.gz"
    with tarfile.open(archive, "w:gz") as handle:
        member = tarfile.TarInfo("../outside")
        payload = b"unsafe"
        member.size = len(payload)
        handle.addfile(member, io.BytesIO(payload))
    with pytest.raises(RuntimeError, match="unsafe path"):
        _safe_extract(archive, tmp_path / "destination")
    assert not (tmp_path / "outside").exists()
