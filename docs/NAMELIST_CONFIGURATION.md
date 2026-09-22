# TOML-controlled WRF namelist options

The case TOML is the user-owned configuration. `wrf-era5-case` translates its
supported keys into `namelist.input`, prints the complete effective values in
`plan`, and records them in `case-manifest.json` and `PHYSICS_PROFILE.md`.

## Example

```toml
[namelist.physics]
bl_pbl_physics = 1
sf_sfclay_physics = 1
sf_surface_physics = 2

[namelist.dynamics]
diff_opt = 2
km_opt = 5

[namelist.time_control]
history_interval = 30

[namelist.domains]
time_step = 45
```

## Currently exposed keys

| TOML section | Accepted WRF keys |
|---|---|
| `namelist.physics` | `mp_physics`, `ra_lw_physics`, `ra_sw_physics`, `radt`, `sf_sfclay_physics`, `sf_surface_physics`, `bl_pbl_physics`, `bldt`, `cu_physics`, `cudt`, `isfflx`, `ifsnow`, `icloud`, `surface_input_source`, `num_soil_layers`, `sf_urban_physics`, `maxiens`, `maxens`, `maxens2`, `maxens3`, `ensdim` |
| `namelist.dynamics` | `w_damping`, `diff_opt`, `km_opt`, `diff_6th_opt`, `diff_6th_factor`, `base_temp`, `damp_opt`, `zdamp`, `dampcoef`, `khdif`, `kvdif`, `non_hydrostatic`, `moist_adv_opt`, `scalar_adv_opt` |
| `namelist.time_control` | `history_interval`, `adjust_output_times`, `frames_per_outfile`, `restart`, `io_form_history`, `io_form_restart`, `io_form_input`, `io_form_boundary` |
| `namelist.domains` | `time_step`, `p_top_requested`, `feedback`, `smooth_option` |

Dates, domain dimensions, spacing and vertical levels remain in the existing
`case` and `domain` sections because they also control ERA5 and WPS generation.
Generated fields such as `max_dom`, start/end arrays and
`num_metgrid_levels` cannot be overridden independently.

## Validation boundary

The package rejects unknown keys and values with the wrong TOML type. It also
checks basic constraints such as positive history intervals and time steps.
It does not yet encode every compatibility rule between WRF schemes. A
configuration that parses successfully is technically well-formed, but still
requires WRF execution and scientific review.

The older `wrf.history_interval_minutes` and `wrf.time_step_seconds` keys remain
supported for existing cases. Values in the newer namespaced tables take
precedence.
