from __future__ import annotations

import math

from .config import CaseConfig


def era5_area(config: CaseConfig) -> tuple[float, float, float, float]:
    """Return a conservative north, west, south, east ERA5 rectangle.

    This is an explicit geometric estimate for the single-domain Lambert MVP,
    not a replacement for projecting the exact WRF corner coordinates.
    """
    half_ns_km = config.dy * (config.e_sn - 1) / 2000.0
    half_ew_km = config.dx * (config.e_we - 1) / 2000.0
    lat_delta = half_ns_km / 111.32 + config.margin_degrees
    cos_lat = max(abs(math.cos(math.radians(config.ref_lat))), 0.1)
    lon_delta = half_ew_km / (111.32 * cos_lat) + config.margin_degrees
    north = min(90.0, config.ref_lat + lat_delta)
    south = max(-90.0, config.ref_lat - lat_delta)
    west = max(-180.0, config.ref_lon - lon_delta)
    east = min(180.0, config.ref_lon + lon_delta)
    return tuple(round(value, 2) for value in (north, west, south, east))
