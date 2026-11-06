from __future__ import annotations

from pathlib import Path


def write_grib(path, request, *, spacing=.25):
    """Small REAL ecCodes GRIB messages; no network or meteorological claims."""
    import eccodes as ec
    import numpy as np
    from wrf_era5_case.grib_cache import PARAMETERS
    north, west, south, east = request["area"]
    ni, nj = round((east-west)/spacing)+1, round((north-south)/spacing)+1
    with Path(path).open("wb") as stream:
        for time in request["time"]:
            for variable in request["variable"]:
                for level in request.get("pressure_level", [0]):
                    h = ec.codes_grib_new_from_samples("regular_ll_pl_grib1" if "pressure_level" in request else "regular_ll_sfc_grib1")
                    try:
                        for key, value in dict(Ni=ni, Nj=nj, latitudeOfFirstGridPointInDegrees=north,
                                               latitudeOfLastGridPointInDegrees=south,
                                               longitudeOfFirstGridPointInDegrees=west,
                                               longitudeOfLastGridPointInDegrees=east,
                                               iDirectionIncrementInDegrees=spacing, jDirectionIncrementInDegrees=spacing,
                                               dataDate=int(''.join(request[k][0] for k in ("year", "month", "day"))),
                                               dataTime=int(time.replace(":", "")), paramId=PARAMETERS[variable], level=int(level)).items():
                            ec.codes_set(h, key, value)
                        ec.codes_set_values(h, np.ones(ni*nj))
                        stream.write(ec.codes_get_message(h))
                    finally:
                        ec.codes_release(h)


def write_config(directory: Path, *, start: str = "2025-01-10 00:00:00", end: str = "2025-01-10 06:00:00") -> Path:
    path = directory / "case.toml"
    path.write_text(f'''[case]
name = "test_case"
start = "{start}"
end = "{end}"
interval_seconds = 3600

[domain]
center_latitude = 52.0
center_longitude = 5.0
true_latitude_1 = 52.0
true_latitude_2 = 52.0
standard_longitude = 5.0
dx = 9000
dy = 9000
nx = 100
ny = 100
vertical_levels = 40

[era5]
forcing_mode = "reanalysis"
directory = "era5"
margin_degrees = 1.0

[geodata]
profile = "low"
directory = "geodata"

[wrf]
physics_profile = "demonstration"
history_interval_minutes = 60
time_step_seconds = 54

[output]
case_directory = "output"
''')
    return path
