import pytest
from conftest import write_grib
from wrf_era5_case.era5 import Era5Request, download_requests
from wrf_era5_case.grib_cache import available, required, inventory


def item(tmp_path, **overrides):
    request = dict(year=["2025"], month=["01"], day=["10"], time=["00:00", "01:00"],
                   variable=["temperature"], pressure_level=["850"], area=[54, 3, 51, 7])
    request.update(overrides)
    return Era5Request("pressure-levels", "reanalysis-era5-pressure-levels", request,
                       tmp_path / "era5-pressure-levels-20250110-test.grib")


def test_downloads_only_missing_hours_and_preserves_original(tmp_path):
    wanted = item(tmp_path)
    original = tmp_path / "era5-pressure-levels-20250110.grib"
    write_grib(original, dict(wanted.request, time=["00:00"]))
    before = original.read_bytes()
    calls = []
    class Client:
        def retrieve(self, dataset, request, target):
            calls.append(request)
            write_grib(target, request)
    downloaded, _ = download_requests([wanted], client_factory=Client)
    assert downloaded == [wanted.target]
    assert [r["time"] for r in calls] == [["01:00"]]
    assert original.read_bytes() == before
    assert available(wanted)


def test_wrong_geography_never_reused(tmp_path):
    wanted = item(tmp_path)
    original = tmp_path / "era5-pressure-levels-20250110.grib"
    write_grib(original, dict(wanted.request, area=[44, 13, 41, 17]))
    assert not available(wanted)
    calls = []
    class Client:
        def retrieve(self, dataset, request, target):
            calls.append(request)
            write_grib(target, request)
    download_requests([wanted], client_factory=Client)
    assert calls[0]["area"] == wanted.request["area"]
    assert calls[0]["time"] == wanted.request["time"]


def test_broader_content_reused_without_network(tmp_path):
    wanted = item(tmp_path)
    write_grib(tmp_path / "era5-pressure-levels-20250110.grib", dict(wanted.request, area=[55, 2, 50, 8]))
    def forbidden():
        raise AssertionError("Unexpected network access")
    downloaded, reused = download_requests([wanted], client_factory=forbidden)
    assert not downloaded and reused == [wanted.target]
    assert inventory(wanted.target, wanted.request).keys() == required(wanted.request)


def test_missing_pressure_level_is_downloaded(tmp_path):
    wanted = item(tmp_path, pressure_level=["850", "500"])
    write_grib(tmp_path / "era5-pressure-levels-20250110.grib", dict(wanted.request, pressure_level=["850"]))
    calls = []
    class Client:
        def retrieve(self, dataset, request, target):
            calls.append(request)
            write_grib(target, request)
    download_requests([wanted], client_factory=Client)
    assert calls[0]["pressure_level"] == ["500"]


def test_incomplete_response_is_rejected_without_publishing(tmp_path):
    wanted = item(tmp_path)
    class Client:
        def retrieve(self, dataset, request, target):
            write_grib(target, dict(request, time=["00:00"]))
    with pytest.raises(RuntimeError, match="does not cover"):
        download_requests([wanted], client_factory=Client)
    assert not wanted.target.exists()


def test_coarser_geographic_superset_is_not_the_requested_product(tmp_path):
    wanted = item(tmp_path)
    write_grib(tmp_path / "era5-pressure-levels-20250110.grib", wanted.request, spacing=1.)
    assert not available(wanted)


def test_downloads_only_missing_variables(tmp_path):
    wanted = item(tmp_path, variable=["temperature", "u_component_of_wind"])
    write_grib(tmp_path / "era5-pressure-levels-20250110.grib", dict(wanted.request, variable=["temperature"]))
    calls = []
    class Client:
        def retrieve(self, dataset, request, target):
            calls.append(request)
            write_grib(target, request)
    download_requests([wanted], client_factory=Client)
    assert calls[0]["variable"] == ["u_component_of_wind"]
