# Demonstration profile

This profile is a transparent technical starting point for the initial
single-domain, 9 km workflow demonstration. It uses WSM5 microphysics, RRTMG
radiation, the Revised MM5 surface layer, Noah land-surface model, YSU PBL and
Kain-Fritsch cumulus parameterization.

These choices are not automatically scientifically suitable for every domain,
resolution, period or research question. Set reviewed overrides in the source
TOML under `[namelist.physics]`, `[namelist.dynamics]`,
`[namelist.time_control]` or `[namelist.domains]`; treat the generated
`namelist.input` as the reproducible result rather than the primary input.
