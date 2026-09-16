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
