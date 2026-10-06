#!/usr/bin/env bash
# Start a local Penpot (open-source design tool) with Docker. Penpot is MPL-2.0; we download its official compose file
# instead of copying it into this repo.   Usage: bash editor/penpot/run.sh [up|down|logs]
set -euo pipefail
cd "$(dirname "$0")"
URL="https://raw.githubusercontent.com/penpot/penpot/main/docker/images/docker-compose.yaml"
[[ -f docker-compose.yaml ]] || { echo "Downloading Penpot's official docker-compose.yaml ..."; curl -fsSL "$URL" -o docker-compose.yaml; }
case "${1:-up}" in
  up)   docker compose -p penpot -f docker-compose.yaml up -d
        echo "Penpot is starting: http://localhost:9001  (first start takes a minute; register a local account)";;
  down) docker compose -p penpot -f docker-compose.yaml down;;
  logs) docker compose -p penpot -f docker-compose.yaml logs -f;;
  *)    echo "usage: $0 [up|down|logs]"; exit 1;;
esac
