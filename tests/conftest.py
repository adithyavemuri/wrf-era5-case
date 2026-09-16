from __future__ import annotations

from pathlib import Path


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
