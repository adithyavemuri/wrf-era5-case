"""Content-checked ERA5 cache. No spatial remapping or geographic tile splicing.

ECMWF parameter IDs: ERA5 data documentation, parameter tables:
https://confluence.ecmwf.int/pages/viewpage.action?pageId=185075432
Every selected message must itself cover the requested geographic rectangle.
"""
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import tempfile

PARAMETERS = dict(zip((
    "geopotential", "relative_humidity", "temperature", "u_component_of_wind", "v_component_of_wind",
    "10m_u_component_of_wind", "10m_v_component_of_wind", "2m_dewpoint_temperature", "2m_temperature",
    "land_sea_mask", "mean_sea_level_pressure", "sea_ice_cover", "sea_surface_temperature", "skin_temperature",
    "snow_depth", "soil_temperature_level_1", "soil_temperature_level_2", "soil_temperature_level_3",
    "soil_temperature_level_4", "surface_pressure", "volumetric_soil_water_layer_1",
    "volumetric_soil_water_layer_2", "volumetric_soil_water_layer_3", "volumetric_soil_water_layer_4",
), (129, 157, 130, 131, 132, 165, 166, 168, 167, 172, 151, 31, 34, 235, 141, 139, 170, 183, 236, 134, 39, 40, 41, 42)))


def required(request):
    levels = [int(x) for x in request.get("pressure_level", [0])]
    date = int(''.join(request[key][0] for key in ("year", "month", "day")))
    return {(PARAMETERS[var], level, date, int(time.replace(":", "")))
            for var in request["variable"] for level in levels for time in request["time"]}


def inventory(path, request):
    """Return matching record -> (file, offset, byte length), without decoding values."""
    import eccodes as ec
    wanted = required(request)
    north, west, south, east = request["area"]
    result = {}
    with Path(path).open("rb") as stream:
        while (handle := ec.codes_grib_new_from_file(stream, headers_only=True)) is not None:
            try:
                kind = ec.codes_get(handle, "typeOfLevel")
                if "pressure_level" in request and kind not in {"isobaricInhPa", "isobaricInPa"}:
                    continue
                if "pressure_level" not in request and kind in {"isobaricInhPa", "isobaricInPa"}:
                    continue
                level = ec.codes_get(handle, "level") if "pressure_level" in request else 0
                if kind == "isobaricInPa":
                    level /= 100
                key = (int(ec.codes_get(handle, "paramId")), int(level),
                       int(ec.codes_get(handle, "validityDate")), int(ec.codes_get(handle, "validityTime")))
                if key not in wanted:
                    continue
                if ec.codes_get(handle, "gridType") != "regular_ll":
                    raise RuntimeError(f"Unsupported ERA5 cache grid in {path}; expected regular_ll")
                if any(not math.isclose(ec.codes_get(handle, key), .25, rel_tol=0, abs_tol=1e-6)
                       for key in ("iDirectionIncrementInDegrees", "jDirectionIncrementInDegrees")):
                    continue  # A coarser regridded cache is not the requested CDS 0.25-degree product.
                lat1 = ec.codes_get(handle, "latitudeOfFirstGridPointInDegrees")
                lat2 = ec.codes_get(handle, "latitudeOfLastGridPointInDegrees")
                lon1 = ec.codes_get(handle, "longitudeOfFirstGridPointInDegrees")
                lon2 = ec.codes_get(handle, "longitudeOfLastGridPointInDegrees")
                width = (ec.codes_get(handle, "Ni") - 1) * ec.codes_get(handle, "iDirectionIncrementInDegrees")
                if width >= 359.:
                    left, right = -180., 180.
                else:
                    left, right = (lon1 + 180) % 360 - 180, (lon2 + 180) % 360 - 180
                    if left > right:
                        raise RuntimeError("Antimeridian-crossing cache grids are not supported")
                if max(lat1, lat2) + 1e-6 >= north and min(lat1, lat2) - 1e-6 <= south and left - 1e-6 <= west and right + 1e-6 >= east:
                    result.setdefault(key, (Path(path), ec.codes_get_message_offset(handle), ec.codes_get_message_size(handle)))
            finally:
                ec.codes_release(handle)
    return result


def candidates(item):
    day = ''.join(item.request[key][0] for key in ("year", "month", "day"))
    return sorted(item.target.parent.glob(f"era5-{item.family}-{day}*.grib"), key=lambda p: (p != item.target, p.name))


def cached_records(item):
    records = {}
    for path in candidates(item):
        try:
            for key, value in inventory(path, item.request).items():
                records.setdefault(key, value)
        except Exception as exc:
            raise RuntimeError(f"Cannot verify cached GRIB {path}: {exc}") from exc
        if records.keys() >= required(item.request):
            break
    return records


def available(item):
    return cached_records(item).keys() >= required(item.request)


def missing_requests(request, missing):
    """Group only missing hours/variables/levels into exact CDS products."""
    grouped = defaultdict(list)
    for time in request["time"]:
        value = int(time.replace(":", ""))
        by_level_set = defaultdict(list)
        for variable in request["variable"]:
            levels = tuple(sorted(level for param, level, _, stamp in missing if param == PARAMETERS[variable] and stamp == value))
            if levels:
                by_level_set[levels].append(variable)
        for levels, variables in by_level_set.items():
            grouped[(levels, tuple(variables))].append(time)
    result = []
    for (levels, variables), times in grouped.items():
        part = dict(request, variable=list(variables), time=times)
        if "pressure_level" in request:
            part["pressure_level"] = [str(level) for level in levels]
        result.append(part)
    return result


def materialize(item, *, force=False, client=None):
    """Reuse checked records and fetch missing ones; atomically publish a case bundle."""
    wanted = required(item.request)
    records = {} if force else cached_records(item)
    if not force and records.keys() >= wanted and item.target.exists() and all(value[0] == item.target for value in records.values()):
        return False
    missing = wanted - records.keys()
    if missing and client is None:
        raise ValueError("A CDS client is needed for missing ERA5 records")
    item.target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".era5-", dir=item.target.parent) as temporary:
        directory = Path(temporary)
        downloads = []
        for index, payload in enumerate(missing_requests(item.request, missing)):
            path = directory / f"download-{index}.grib"
            client.retrieve(item.dataset, payload, str(path))
            found = inventory(path, payload)
            if found.keys() < required(payload):
                raise RuntimeError("CDS GRIB response does not cover requested coordinates/times/fields/levels; cache unchanged")
            downloads.append({"request": payload, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
            records.update(found)
        if records.keys() < wanted:
            raise RuntimeError("ERA5 coverage incomplete; refusing to prepare a forcing bundle")
        bundle = directory / "bundle.grib"
        with bundle.open("wb") as output:
            for key in sorted(wanted):
                path, offset, size = records[key]
                with path.open("rb") as stream:
                    stream.seek(offset)
                    output.write(stream.read(size))
        if inventory(bundle, item.request).keys() < wanted:
            raise RuntimeError("Assembled ERA5 bundle failed its content check")
        metadata = {"dataset": item.dataset, "request": item.request,
                    "sources": sorted({value[0].name for value in records.values() if value[0].parent != directory}),
                    "downloads": downloads, "sha256": hashlib.sha256(bundle.read_bytes()).hexdigest()}
        bundle.replace(item.target)
        item.target.with_suffix(".coverage.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return bool(missing)
