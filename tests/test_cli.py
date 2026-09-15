from __future__ import annotations

import pytest

from conftest import write_config
from wrf_era5_case.cli import main


def test_plan_is_read_only(tmp_path, capsys):
    config = write_config(tmp_path)
    with pytest.raises(SystemExit) as result:
        main(["plan", str(config)])
    assert result.value.code == 0
    assert "No files were written or downloaded" in capsys.readouterr().out
    assert not (tmp_path / "output").exists()


def test_requests_write_auditable_json(tmp_path):
    config = write_config(tmp_path)
    with pytest.raises(SystemExit) as result:
        main(["requests", str(config)])
    assert result.value.code == 0
    files = sorted((tmp_path / "output" / "requests").glob("*.json"))
    assert len(files) == 2


def test_check_reports_missing_user_credentials(tmp_path, monkeypatch, capsys):
    config = write_config(tmp_path)
    home = tmp_path / "empty-home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    with pytest.raises(SystemExit) as result:
        main(["check", str(config)])
    assert result.value.code == 1
    assert "~/.cdsapirc was not found" in capsys.readouterr().out
