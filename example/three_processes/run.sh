#!/usr/bin/env bash
# Runs permissions_app as three Python processes talking through remote's signed JSON-RPC calls:
#   storage  (MemoryStorage, http://localhost:8201)
#   backend  (Manager, use cases, permissions, HTTP API, http://localhost:8202) -- its IStorage is the storage's
#   frontend (the terminal admin console)                                      -- its services are the backend's
# The first two run in the background (logs/storage.log, logs/backend.log); the console takes this terminal
# (its own logs: logs/frontend.log).
# Log in as admin / admin. Quitting the console stops the other two. Run from anywhere.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
HERE="$(pwd)"
PROJECT="$(cd ../.. && pwd)"
REPOSITORIES="$(cd ../../.. && pwd)"
RUN=(uv run --project "$PROJECT" --with-editable "$REPOSITORIES/http_server" --with-editable "$REPOSITORIES/remote")

mkdir -p logs
"${RUN[@]}" --directory "$HERE/storage" python -m ycappuccino.core.runner --root_path . > logs/storage.log 2>&1 &
STORAGE=$!
"${RUN[@]}" --directory "$HERE/backend" python -m ycappuccino.core.runner --root_path . > logs/backend.log 2>&1 &
BACKEND=$!
trap 'kill "$STORAGE" "$BACKEND" 2>/dev/null || true' EXIT

"${RUN[@]}" --directory "$HERE/frontend" python run.py
