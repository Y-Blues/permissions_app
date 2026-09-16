#!/usr/bin/env bash
# Launches the permissions_app console (login as superadmin/demo, then manage tenants, roles,
# permissions and users). Run from anywhere -- it cd's into this script's own directory first.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
uv run --project ../.. python run.py
