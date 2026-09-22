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
    wrf = outputs["namelist_input"].read_text()
    assert "2025-01-10_00:00:00" in wps
    assert "2025-01-10_06:00:00" in wps
    assert "prefix = 'ERA5'" in wps
    assert "fg_name = 'ERA5'" in wps
    assert not (config.case_directory / "namelist.wps.pressure").exists()
    assert not (config.case_directory / "namelist.wps.surface").exists()
    assert "geog_data_res     = 'lowres'" in wps
    assert "adjust_output_times                 = .true." in (config.case_directory / "namelist.input").read_text()
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


def test_writes_toml_namelist_overrides_and_manifest(tmp_path):
    source = write_config(tmp_path)
    source.write_text(source.read_text() + "\n[namelist.dynamics]\ndiff_opt = 2\nkm_opt = 5\n")
    config = load_config(source)
    outputs = configure_case(config, build_requests(config))
    namelist = outputs["namelist_input"].read_text()
    assert "diff_opt                            = 2" in namelist
    assert "km_opt                              = 5" in namelist
    manifest = json.loads(outputs["manifest"].read_text())
    assert manifest["effective_namelist"]["dynamics"]["km_opt"] == 5


def test_writes_nested_domain_arrays(tmp_path):
    source = write_config(tmp_path)
    text = source.read_text().replace("[domain]", "[[domain]]", 1)
    text += '''

[[domain]]
name = "d02"
parent_id = 1
parent_grid_ratio = 3
parent_time_step_ratio = 3
i_parent_start = 25
j_parent_start = 25
nx = 151
ny = 151
vertical_levels = 40
'''
    source.write_text(text)
    config = load_config(source)
    outputs = configure_case(config, build_requests(config))
    wps = outputs["namelist_wps"].read_text()
    wrf = outputs["namelist_input"].read_text()
    assert "max_dom = 2" in wps
    assert "parent_grid_ratio = 1, 3" in wps
    assert "e_we              = 100, 151" in wps
    assert "max_dom                             = 2" in wrf
    assert "dx                                  = 9000, 3000" in wrf
    assert "history_interval                    = 60, 60" in wrf
    assert "bl_pbl_physics                      = 1, 1" in wrf
    assert "km_opt                              = 4, 4" in wrf
    assert "nested                              = .false., .true." in wrf


def test_projection_selection_reaches_wps_namelist(tmp_path):
    source = write_config(tmp_path)
    source.write_text(source.read_text().replace("[era5]", 'map_projection = "mercator"\n\n[era5]'))
    config = load_config(source)
    outputs = configure_case(config, build_requests(config))
    assert "map_proj = 'mercator'" in outputs["namelist_wps"].read_text()


def test_custom_eta_levels_and_automatic_restart_interval(tmp_path):
    source = write_config(tmp_path)
    eta = [1.0, .95, .9, .8, .7, .6, .5, .4, .3, .2, 0.0]
    text = source.read_text().replace("vertical_levels = 40", "vertical_levels = 11")
    text += "\n[vertical_grid]\neta_levels = [" + ", ".join(map(str, eta)) + "]\n"
    source.write_text(text)
    config = load_config(source)
    namelist = configure_case(config, build_requests(config))["namelist_input"].read_text()
    assert "eta_levels" in namelist
    assert "1, 0.95, 0.9" in namelist
    assert "restart_interval                    = 180" in namelist
