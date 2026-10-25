#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "== $(date -Is) sync"
sudo docker compose run --rm -T api python -m radar.sync
echo "== $(date -Is) enriquecer"
sudo docker compose run --rm -T api python -m radar.enriquecer --limite 6000
echo "== $(date -Is) fim"
