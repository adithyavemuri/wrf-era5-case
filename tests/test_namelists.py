from __future__ import annotations

import json

import pytest

from conftest import write_config
from wrf_era5_case.config import load_config
from wrf_era5_case.domain import era5_area
from wrf_era5_case.era5 import build_requests
from wrf_era5_case.namelists import configure_case


def test_area_is_conservative_and_bounded(tmp_path):
    config = load_config(write_config(tmp_path))
    north, west, south, east = era5_area(config)
    assert north > config.ref_lat > south
    assert west < config.ref_lon < east


def test_generates_readable_synchronized_namelists(tmp_path):
    config = load_config(write_config(tmp_path))
    outputs = configure_case(config, build_requests(config))
    wps = outputs["namelist_wps"].read_text()
    surface_wps = outputs["namelist_wps_surface"].read_text()
    wrf = outputs["namelist_input"].read_text()
    assert "2025-01-10_00:00:00" in wps
    assert "2025-01-10_06:00:00" in wps
    assert "prefix = 'PRES'" in wps
    assert "prefix = 'SFC'" in surface_wps
    assert "geog_data_res     = 'lowres'" in wps
    assert "run_hours                           = 6" in wrf
    assert "num_metgrid_levels                  = 38" in wrf
    assert "bl_pbl_physics                      = 1" in wrf
    assert "@" not in wps + wrf
    manifest = json.loads(outputs["manifest"].read_text())
    assert manifest["case"] == "test_case"
    assert len(manifest["inputs"]["era5_requests"]) == 2


def test_reuses_matching_case_and_protects_human_edits(tmp_path):
    config = load_config(write_config(tmp_path))
    first = configure_case(config, build_requests(config))
    created = json.loads(first["manifest"].read_text())["created_utc"]
    configure_case(config, build_requests(config))
    assert json.loads(first["manifest"].read_text())["created_utc"] == created
    first["namelist_input"].write_text(first["namelist_input"].read_text() + "! user edit\n")
    with pytest.raises(RuntimeError, match="prepare --force-config"):
        configure_case(config, build_requests(config))
    configure_case(config, build_requests(config), force=True)
    assert "user edit" not in first["namelist_input"].read_text()
