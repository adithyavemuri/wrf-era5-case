from __future__ import annotations

from conftest import write_config
from wrf_era5_case.config import load_config
from wrf_era5_case.era5 import build_requests, download_requests, is_grib, requested_times


def test_requests_are_exact_and_split_by_day(tmp_path):
    config = load_config(write_config(
        tmp_path, start="2025-01-31 23:00:00", end="2025-02-01 01:00:00"
    ))
    assert [value.strftime("%Y-%m-%d %H:%M") for value in requested_times(config)] == [
        "2025-01-31 23:00", "2025-02-01 00:00", "2025-02-01 01:00"
    ]
    requests = build_requests(config)
    assert len(requests) == 4
    assert requests[0].request["time"] == ["23:00"]
    assert requests[2].request["month"] == ["02"]
    assert requests[2].request["time"] == ["00:00", "01:00"]
    assert len(requests[0].request["pressure_level"]) == 37


def test_download_is_atomic_and_reusable(tmp_path):
    config = load_config(write_config(tmp_path, end="2025-01-10 01:00:00"))
    requests = build_requests(config)

    class Client:
        def retrieve(self, dataset, request, target):
            with open(target, "wb") as handle:
                handle.write(b"GRIB" + b"0" * 20)

    def must_not_connect():
        raise AssertionError("client factory should not run when all GRIB files are reusable")

    downloaded, reused = download_requests(requests, client_factory=Client)
    assert len(downloaded) == 2
    assert not reused
    assert all(is_grib(path) for path in downloaded)
    downloaded, reused = download_requests(requests, client_factory=must_not_connect)
    assert not downloaded
    assert len(reused) == 2
    assert not list(config.era5_directory.glob("*.part"))
