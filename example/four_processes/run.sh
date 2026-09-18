#!/usr/bin/env bash
# Runs permissions_app as four Python processes talking through remote's signed JSON-RPC calls:
#   storage   http://localhost:8301  MemoryStorage
#   usecases  http://localhost:8302  Manager, use cases, permissions         -- its IStorage is the storage's
#   http      http://localhost:8303  the public API (JWT, CORS, JSON-RPC)    -- its use cases are the usecases'
#   web       http://localhost:8304  the web front (page, theme, wheels)     -- the browser calls the http API
# Open http://localhost:8304 and log in as admin / admin. Logs: logs/*.log. Ctrl+C stops all four.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
HERE="$(pwd)"
PROJECT="$(cd ../.. && pwd)"
REPOSITORIES="$(cd ../../.. && pwd)"
RUN=(uv run --project "$PROJECT" --with-editable "$REPOSITORIES/http_server" --with-editable "$REPOSITORIES/remote"
     --with-editable "$REPOSITORIES/hosts")

# the web front's site: the generic client page, this deployment's configuration and theme, the wheels
rm -rf web/site
mkdir -p web/site/wheels logs
for repository in api core client ui ui_web permissions_app; do
  (cd "$REPOSITORIES/$repository" && uv build --wheel --quiet --out-dir "$HERE/web/site/wheels")
done
cp "$REPOSITORIES/client/static/index.html" web/site/index.html
cp web/ycappuccino.json web/site/ycappuccino.json
cp ../web/style.css web/site/style.css

PIDS=()
for process in storage usecases http web; do
  "${RUN[@]}" --directory "$HERE/$process" python -m ycappuccino.core.runner --root_path . > "logs/$process.log" 2>&1 &
  PIDS+=($!)
done
trap 'kill "${PIDS[@]}" 2>/dev/null || true' EXIT

echo "http://localhost:8304  (admin / admin) -- Ctrl+C stops the four processes"
wait
