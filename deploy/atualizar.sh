#!/usr/bin/env bash
# Atualização diária (cron, 4h): retrato novo do PNCP e itens das licitações novas.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "== $(date -Is) sync"
sudo docker compose run --rm -T api python -m radar.sync
echo "== $(date -Is) enriquecer"
sudo docker compose run --rm -T api python -m radar.enriquecer --limite 6000
echo "== $(date -Is) fim"
