from __future__ import annotations

import math

from .config import CaseConfig


def era5_area(config: CaseConfig) -> tuple[float, float, float, float]:
    """Return the ERA5 rectangle enclosing the projected outer-domain corners."""
    radius = 6_370_000.0
    lon0 = math.radians(config.stand_lon)
    lat0 = math.radians(config.ref_lat)
    lon_ref = math.radians(config.ref_lon)
    if config.map_projection == "lambert":
        phi1 = math.radians(config.truelat1); phi2 = math.radians(config.truelat2)
        n = math.sin(phi1) if abs(phi1 - phi2) < 1e-12 else math.log(math.cos(phi1) / math.cos(phi2)) / math.log(math.tan(math.pi/4 + phi2/2) / math.tan(math.pi/4 + phi1/2))
        factor = math.cos(phi1) * math.tan(math.pi/4 + phi1/2) ** n / n
        def rho(phi): return radius * factor / math.tan(math.pi/4 + phi/2) ** n
        rho0 = rho(lat0); rho_ref = rho(lat0)
        centre_x = rho_ref * math.sin(n * (lon_ref - lon0)); centre_y = rho0 - rho_ref * math.cos(n * (lon_ref - lon0))
        def inverse(x, y):
            radial = math.copysign(math.hypot(x, rho0-y), n)
            theta = math.atan2(x, rho0-y)
            return 2*math.atan((radius*factor/radial)**(1/n))-math.pi/2, lon0+theta/n
    else:
        centre_x = radius * (lon_ref - lon0)
        centre_y = radius * math.log(math.tan(math.pi/4 + lat0/2))
        def inverse(x, y):
            return 2*math.atan(math.exp(y/radius))-math.pi/2, lon0+x/radius
    half_x = config.dx * (config.e_we - 1) / 2
    half_y = config.dy * (config.e_sn - 1) / 2
    corners = [inverse(centre_x+x, centre_y+y) for x in (-half_x,half_x) for y in (-half_y,half_y)]
    latitudes = [math.degrees(item[0]) for item in corners]; longitudes = [math.degrees(item[1]) for item in corners]
    north = min(90.0, max(latitudes) + config.margin_degrees)
    south = max(-90.0, min(latitudes) - config.margin_degrees)
    west = max(-180.0, min(longitudes) - config.margin_degrees)
    east = min(180.0, max(longitudes) + config.margin_degrees)
    return tuple(round(value, 2) for value in (north, west, south, east))
