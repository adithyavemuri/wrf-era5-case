# Acceptance validation

The Netherlands demonstration case was validated locally on 2026-09-16. This
test proves that the package's generated ERA5 requests and namelists can feed a
real WPS/WRF preprocessing chain. It does not establish scientific suitability
for a particular research question.

This is an ERA5-reanalysis-forced WRF simulation, not a newly generated
reanalysis product.

## Tested case

- Configuration: `examples/netherlands-demo.toml`
- Period: 2025-01-10 00:00 through 06:00 UTC
- Domain: one 100 x 100 Lambert grid at 9 km spacing
- ERA5: seven hourly states from the CDS pressure-level and single-level
  reanalysis datasets
- Pressure levels: all 37 configured ERA5 levels
- WPS geodata: official low-resolution mandatory package
- WPS: 4.6.0
- WRF: 4.7.1, GNU/MPICH `dmpar` build, `em_real`

## Verified chain

1. The authenticated CDS downloads produced one pressure-level and one
   single-level GRIB file.
2. The WPS GRIB reader found the intended pressure-level variables and all 37
   levels, plus the requested surface and soil fields, for every hour.
3. `geogrid.exe` completed using the `lowres` interpolation names required by
   the low-resolution geodata package.
4. A named-run acceptance test on 2026-09-21 combined both GRIB inputs in one
   `ungrib.exe` pass using WPS `Vtable.ECMWF` and produced seven hourly `ERA5:*`
   intermediate states.
5. `metgrid.exe` produced seven hourly `met_em.d01.*.nc` files.
6. `real.exe` ran with four MPI ranks. Every rank reported
   `SUCCESS COMPLETE REAL_EM INIT`.
7. WRF initialization produced non-empty `wrfinput_d01` and `wrfbdy_d01`
   files (approximately 34 MB and 36 MB respectively).

The generated validation products remain under the ignored `cases/` tree and
are not part of the source distribution. CDS credentials, downloaded ERA5 data
and generated WRF inputs are not tracked.

## What remains

- Run and evaluate `wrf.exe`; this package deliberately stops at case
  preparation and does not currently execute or monitor simulations.
- Obtain scientific review of the demonstration physics choices.
- Test the high-resolution geodata profile and additional domains/dates.
- Build and inspect release artifacts on the supported Python versions.
