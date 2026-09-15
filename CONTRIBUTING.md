# Contributing

Keep changes within the documented WRF-only scope and preserve the transparent
configuration model: scientific and namelist choices must remain visible to
users rather than being hidden in orchestration code.

Before opening a pull request:

```bash
. .venv/bin/activate
python -m pytest
bash -n install_local.sh
wrf-era5-case plan examples/netherlands-demo.toml
```

Tests must not contact CDS or download WPS geographical data. Network clients
must be replaceable with test doubles. Changes to ERA5 variables, pressure
levels, Vtables or namelists require a documented WPS and `real.exe`
acceptance test.
