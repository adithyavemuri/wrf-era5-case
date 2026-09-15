from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .config import CaseConfig, ConfigurationError, load_config
from .domain import era5_area
from .era5 import build_requests, download_requests, is_grib, requested_times, write_request_files
from .geodata import GEODATA_COMPRESSED_BYTES, GEODATA_URLS, download_geodata, geodata_status
from .namelists import configure_case
from .validation import checks_pass, run_checks


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wrf-era5-case",
        description="Prepare transparent ERA5-driven WRF cases without root access.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (
        ("check", "Check local prerequisites and existing inputs"),
        ("plan", "Show the exact case and download plan without writing files"),
        ("requests", "Write reproducible CDS request JSON files without downloading"),
        ("download-era5", "Download or reuse the required daily ERA5 GRIB files"),
        ("configure", "Generate human-editable WPS and WRF namelists"),
        ("prepare", "Download inputs and generate the complete case directory"),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("config", type=Path)
        if name in {"download-era5", "configure", "prepare"}:
            command.add_argument("--force", action="store_true", help="Explicitly replace this command's existing outputs")

    geodata = commands.add_parser("geodata", help="Inspect or download shared mandatory WPS geographical data")
    geodata_commands = geodata.add_subparsers(dest="geodata_command", required=True)
    status = geodata_commands.add_parser("status", help="Report whether mandatory geodata are installed")
    status.add_argument("config", type=Path)
    download = geodata_commands.add_parser("download", help="Download and extract the configured geodata package")
    download.add_argument("config", type=Path)
    download.add_argument("--force", action="store_true", help="Redownload and re-extract the configured package")
    return parser


def _print_checks(config: CaseConfig) -> bool:
    checks = run_checks(config)
    for item in checks:
        print(f"{item.status:4}  {item.name}: {item.detail}")
    return checks_pass(checks)


def _print_plan(config: CaseConfig) -> None:
    times = requested_times(config)
    requests = build_requests(config)
    north, west, south, east = era5_area(config)
    available = sum(is_grib(item.target) for item in requests)
    print(f"Case:                 {config.name}")
    print(f"Period (UTC):         {config.start.isoformat(' ')} to {config.end.isoformat(' ')}")
    print(f"Duration:             {config.duration_seconds / 3600:g} hours")
    print(f"ERA5 times:           {len(times)} hourly states, including the end time")
    print(f"ERA5 area (N/W/S/E):  {north}, {west}, {south}, {east}")
    print(f"ERA5 daily requests:  {len(requests)} ({len(requests) // 2} days x 2 data families)")
    print(f"ERA5 files available: {available} of {len(requests)}")
    print(f"Pressure levels:      {len(config.pressure_levels)}")
    print(f"Geodata profile:      {config.geography_profile}")
    print(f"Geodata download:     approximately {GEODATA_COMPRESSED_BYTES[config.geography_profile] / 1024**3:.2f} GiB compressed")
    print(f"Geodata directory:    {config.geography_directory}")
    print(f"ERA5 directory:       {config.era5_directory}")
    print(f"Case directory:       {config.case_directory}")
    print(f"Physics profile:      {config.physics_profile} (technical demonstration only)")
    print("\nNo files were written or downloaded.")
    print("The ERA5 rectangle is a conservative estimate; inspect it before downloading.")


def _require_cds_prerequisites(config: CaseConfig) -> None:
    failed = [item for item in run_checks(config) if item.status == "FAIL" and item.name in {"CDS credentials", "CDS client"}]
    if failed:
        raise RuntimeError("; ".join(item.detail for item in failed))


def _require_geodata(config: CaseConfig) -> None:
    status = geodata_status(config)
    if not status["installed"]:
        raise RuntimeError(
            f"mandatory WPS geodata were not found under {config.geography_directory}; "
            f"run 'wrf-era5-case geodata download {config.source}' first"
        )


def _run(arguments: argparse.Namespace) -> int:
    config = load_config(arguments.config)
    command = arguments.command
    if command == "check":
        return 0 if _print_checks(config) else 1
    if command == "plan":
        _print_plan(config)
        return 0
    if command == "requests":
        paths = write_request_files(config, build_requests(config))
        print(f"Wrote {len(paths)} request files under {config.case_directory / 'requests'}")
        return 0
    if command == "geodata":
        if arguments.geodata_command == "status":
            print(json.dumps(geodata_status(config), indent=2))
        else:
            print(f"Downloading {config.geography_profile}-resolution mandatory WPS geodata")
            print(f"Source: {GEODATA_URLS[config.geography_profile]}")
            root = download_geodata(config, force=arguments.force)
            print(f"WPS geodata ready: {root}")
        return 0
    if command == "download-era5":
        _require_cds_prerequisites(config)
        requests = build_requests(config)
        write_request_files(config, requests)
        downloaded, reused = download_requests(requests, force=arguments.force)
        print(f"ERA5 ready: {len(downloaded)} downloaded, {len(reused)} reused")
        return 0
    if command == "configure":
        _require_geodata(config)
        outputs = configure_case(config, build_requests(config), force=arguments.force)
        for label, path in outputs.items():
            print(f"{label}: {path}")
        return 0
    if command == "prepare":
        _require_cds_prerequisites(config)
        print("[1/4] Preparing shared WPS geodata")
        root = download_geodata(config)
        print(f"      {root}")
        print("[2/4] Writing reproducible ERA5 request files")
        requests = build_requests(config)
        write_request_files(config, requests)
        print("[3/4] Downloading or reusing ERA5 GRIB files")
        downloaded, reused = download_requests(requests, force=arguments.force)
        print(f"      {len(downloaded)} downloaded, {len(reused)} reused")
        print("[4/4] Generating readable case configuration")
        configure_case(config, requests, force=arguments.force)
        print(f"Case prepared: {config.case_directory}")
        print("Next: inspect the namelists, then validate this case with WPS and real.exe.")
        return 0
    raise RuntimeError(f"unsupported command: {command}")


def main(argv: list[str] | None = None) -> None:
    try:
        raise SystemExit(_run(_parser().parse_args(argv)))
    except (ConfigurationError, RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
