#!/usr/bin/env bash
# Uso: bash deploy/setup.sh [dominio]   (sem domínio, responde em http://IP)
set -euo pipefail

DOMINIO="${1:-}"
PASTA="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PASTA"

if [ ! -f .env ]; then
  echo "Falta o .env com GROQ_API_KEY e GEMINI_API_KEY. Copie: cp .env.example .env e preencha." >&2
  exit 1
fi

if ! swapon --show | grep -q .; then
  sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
  sudo mkswap /swapfile && sudo swapon /swapfile
  echo "/swapfile none swap sw 0 0" | sudo tee -a /etc/fstab >/dev/null
fi

if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER"
fi

# As imagens Ubuntu da Oracle bloqueiam 80/443 no iptables mesmo com a Security List aberta.
for porta in 80 443; do
  sudo iptables -C INPUT -p tcp --dport "$porta" -j ACCEPT 2>/dev/null \
    || sudo iptables -I INPUT 1 -p tcp --dport "$porta" -j ACCEPT
done
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq iptables-persistent >/dev/null && sudo netfilter-persistent save

if [ -n "$DOMINIO" ]; then
  grep -q "^DOMINIO=" .env && sed -i "s/^DOMINIO=.*/DOMINIO=$DOMINIO/" .env || echo "DOMINIO=$DOMINIO" >> .env
fi

mkdir -p data logs
sudo docker compose --env-file .env up -d --build

if [ ! -f data/radar.db ]; then
  echo "Primeira carga do banco em segundo plano (sync ~10 min, enriquecimento ~1h30). Log em logs/."
  nohup bash deploy/atualizar.sh >> logs/atualizar.log 2>&1 &
fi

LINHA="0 4 * * * cd $PASTA && bash deploy/atualizar.sh >> logs/atualizar.log 2>&1"
( crontab -l 2>/dev/null | grep -v "deploy/atualizar.sh" ; echo "$LINHA" ) | crontab -

echo "Pronto. Teste: curl http://localhost/api/health"
