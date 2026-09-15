#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${WRF_ERA5_CASE_VENV:-$PROJECT_DIR/.venv}"

python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install --editable "$PROJECT_DIR"

printf 'Installed wrf-era5-case in %s\n' "$VENV_DIR"
printf 'Activate with: . %s/bin/activate\n' "$VENV_DIR"
