from __future__ import annotations

import pytest

from conftest import write_config
from wrf_era5_case.config import ConfigurationError, load_config


def test_loads_human_readable_case(tmp_path):
    config = load_config(write_config(tmp_path))
    assert config.name == "test_case"
    assert config.duration_seconds == 6 * 3600
    assert config.e_we == 100
    assert len(config.pressure_levels) == 37
    assert config.forcing_mode == "reanalysis"
    assert config.era5_directory == (tmp_path / "era5").resolve()
    assert config.namelist_options["physics"]["bl_pbl_physics"] == 1
    assert config.namelist_options["dynamics"]["km_opt"] == 4


def test_rejects_non_hour_boundary(tmp_path):
    path = write_config(tmp_path, start="2025-01-10 00:30:00")
    with pytest.raises(ConfigurationError, match="complete hours"):
        load_config(path)


def test_rejects_reverse_period(tmp_path):
    path = write_config(tmp_path, start="2025-01-11 00:00:00", end="2025-01-10 00:00:00")
    with pytest.raises(ConfigurationError, match="later"):
        load_config(path)


def test_converts_explicit_timezone_to_utc(tmp_path):
    path = write_config(
        tmp_path, start="2025-01-10T01:00:00+01:00", end="2025-01-10T07:00:00+01:00"
    )
    config = load_config(path)
    assert config.start.isoformat() == "2025-01-10T00:00:00"
    assert config.end.isoformat() == "2025-01-10T06:00:00"


def test_rejects_non_reanalysis_forcing(tmp_path):
    path = write_config(tmp_path)
    text = path.read_text().replace('forcing_mode = "reanalysis"', 'forcing_mode = "forecast"')
    path.write_text(text)
    with pytest.raises(ConfigurationError, match="reanalysis.*only"):
        load_config(path)


def test_accepts_validated_namelist_overrides(tmp_path):
    path = write_config(tmp_path)
    path.write_text(path.read_text() + '''

[namelist.physics]
bl_pbl_physics = 2

[namelist.dynamics]
diff_opt = 2
km_opt = 5

[namelist.time_control]
history_interval = 30

[namelist.domains]
time_step = 45
''')
    config = load_config(path)
    assert config.namelist_options["physics"]["bl_pbl_physics"] == 2
    assert config.namelist_options["dynamics"]["diff_opt"] == 2
    assert config.namelist_options["dynamics"]["km_opt"] == 5
    assert config.history_interval_minutes == 30
    assert config.time_step_seconds == 45


def test_rejects_unknown_namelist_key(tmp_path):
    path = write_config(tmp_path)
    path.write_text(path.read_text() + "\n[namelist.dynamics]\nkm_opts = 5\n")
    with pytest.raises(ConfigurationError, match="unsupported keys.*km_opts"):
        load_config(path)


def test_rejects_wrong_namelist_value_type(tmp_path):
    path = write_config(tmp_path)
    path.write_text(path.read_text() + '\n[namelist.dynamics]\nkm_opt = "five"\n')
    with pytest.raises(ConfigurationError, match="km_opt must be a int"):
        load_config(path)


def test_loads_and_validates_nested_domains(tmp_path):
    path = write_config(tmp_path)
    text = path.read_text().replace("[domain]", "[[domain]]", 1)
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
    path.write_text(text)
    config = load_config(path)
    assert len(config.domains) == 2
    assert config.domains[1].dx == 3000
    assert config.domains[1].dy == 3000


def test_rejects_nested_domain_outside_parent(tmp_path):
    path = write_config(tmp_path)
    text = path.read_text().replace("[domain]", "[[domain]]", 1)
    text += '''

[[domain]]
parent_id = 1
parent_grid_ratio = 3
i_parent_start = 80
j_parent_start = 80
nx = 151
ny = 151
'''
    path.write_text(text)
    with pytest.raises(ConfigurationError, match="does not fit"):
        load_config(path)


def test_rejects_two_way_feedback(tmp_path):
    path = write_config(tmp_path)
    path.write_text(path.read_text() + "\n[namelist.domains]\nfeedback = 1\n")
    with pytest.raises(ConfigurationError, match="one-way nesting"):
        load_config(path)


def test_accepts_mercator_projection(tmp_path):
    path = write_config(tmp_path)
    path.write_text(path.read_text().replace("[era5]", 'map_projection = "mercator"\n\n[era5]'))
    assert load_config(path).map_projection == "mercator"
