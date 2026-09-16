# Release checklist

- [ ] Run the offline tests on Python 3.10 and 3.12.
- [ ] Confirm `plan` and `requests` do not access the network.
- [ ] Confirm a missing `.cdsapirc` fails before an ERA5 request.
- [x] Complete a minimal authenticated ERA5 pressure/surface download.
- [x] Inspect the GRIB messages with WPS `g1print.exe`/`g2print.exe`.
- [x] Run `geogrid.exe`, both `ungrib.exe` passes and `metgrid.exe`.
- [x] Confirm all expected `met_em.d01` hours are present.
- [x] Run `real.exe` and verify `wrfinput_d01` and `wrfbdy_d01`.
- [x] Record the tested WRF, WPS and data versions.
- [ ] Review the demonstration physics profile with a WRF domain expert.
- [ ] Confirm no credentials, downloaded data or generated cases are tracked.
- [ ] Build and inspect the wheel and source distribution.
