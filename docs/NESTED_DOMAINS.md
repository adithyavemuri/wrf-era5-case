# One-way nested domains

Use one `[[domain]]` table per stationary domain. Domains are ordered `d01`,
`d02`, and so on. The first table defines the map projection and outer grid;
each child references an earlier parent by numeric `parent_id`.

```toml
[[domain]]
name = "d01"
center_latitude = 52.0
center_longitude = 5.0
dx = 9000
dy = 9000
nx = 100
ny = 100
vertical_levels = 40

[[domain]]
name = "d02"
parent_id = 1
parent_grid_ratio = 3
parent_time_step_ratio = 3
i_parent_start = 25
j_parent_start = 25
nx = 151
ny = 151
vertical_levels = 40
```

Child `dx` and `dy` are derived from the parent and grid ratio unless supplied
explicitly. The package verifies parent ordering, positive dimensions, exact
spacing ratios, divisible child dimensions, and that each child fits inside
its parent.

The generated WPS and WRF namelists contain the required domain arrays. The
workflow stages all `met_em.d??` files, requires an initialization file and a
complete final output for every domain, and sends the domain selected by
`analysis.domain` to WRF_tools.

Current scope is stationary one-way nesting (`feedback = 0`). Two-way nesting,
moving nests, automatic nest placement and independent physics per domain are
not yet supported. The example geometry is a technical demonstration and must
be reviewed before research use.

The bundled example has passed WPS and `real.exe` initialization, a six-hour
`wrf.exe` simulation for both domains, and WRF_tools PDF generation for the
configured `d02` analysis domain.
