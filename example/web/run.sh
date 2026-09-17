#!/usr/bin/env bash
# Launches permissions_app with its browser console: builds the wheels the browser installs into site/,
# next to the generic client page, ycappuccino.json and style.css (this deployment's theme, linked by
# ycappuccino.json), then starts the backend, which serves /api and site/ on http://localhost:8180.
# Open that URL, log in as admin / admin. Run from anywhere.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
REPOSITORIES="$(cd ../../.. && pwd)"

rm -rf site
mkdir -p site/wheels
for repository in api core client ui ui_web permissions_app; do
  (cd "$REPOSITORIES/$repository" && uv build --wheel --quiet --out-dir "$OLDPWD/site/wheels")
done
cp "$REPOSITORIES/client/static/index.html" site/index.html
cp ycappuccino.json site/ycappuccino.json
cp style.css site/style.css

echo "http://localhost:8180  (admin / admin)"
uv run --project ../.. \
  --with-editable "$REPOSITORIES/http_server" \
  --with-editable "$REPOSITORIES/remote" \
  --with-editable "$REPOSITORIES/hosts" \
  python -m ycappuccino.core.runner --root_path .
