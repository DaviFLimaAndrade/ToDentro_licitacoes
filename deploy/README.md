# Deploy na Oracle Cloud (Always Free)

Uma VM roda tudo: a API com o React (FastAPI + uvicorn), o Caddy com HTTPS e o cron que atualiza o banco às 4h.

## 1. No painel da Oracle (uma vez)

1. Crie a conta em [cloud.oracle.com](https://cloud.oracle.com). Escolha a região **Brazil East (São Paulo)**: ela não muda depois, e IP brasileiro evita bloqueio no PNCP.
2. **Compute → Instances → Create instance**
   - Image: **Canonical Ubuntu 24.04**
   - Shape: **VM.Standard.A1.Flex** (Ampere, 1 OCPU, 6 GB) se houver vaga; senão **VM.Standard.E2.1.Micro**
   - Em *Add SSH keys*, baixe a chave privada e guarde
3. Na instância, abra a **Subnet → Security List → Add Ingress Rules**: origem `0.0.0.0/0`, TCP, portas **80** e **443**.
4. Anote o **IP público** da instância.

Domínio (opcional): crie um subdomínio grátis em [duckdns.org](https://www.duckdns.org) apontando para o IP. Sem domínio, o site responde em `http://IP`, sem HTTPS.

## 2. Na VM

```bash
ssh -i chave.key ubuntu@IP
git clone https://github.com/DaviFLimaAndrade/ToDentro_licitacoes.git radar && cd radar
cp .env.example .env && nano .env        # GROQ_API_KEY e GEMINI_API_KEY
bash deploy/setup.sh radar-licitacoes.duckdns.org   # ou sem argumento, para usar só o IP
```

O `setup.sh` cria 2 GB de swap, instala o Docker, libera as portas 80 e 443 no iptables da VM, sobe os containers, agenda a atualização diária e, na primeira vez, carrega o banco em segundo plano. O sync leva ~10 min e o enriquecimento ~1h30; acompanhe em `logs/atualizar.log`.

## 3. Conferir

```bash
curl http://localhost/api/health          # {"ok": true, "licitacoes": ...}
sudo docker compose ps
tail -f logs/atualizar.log
```

Até o primeiro sync terminar, `/api/health` responde 503 (banco vazio).

## Atualizar o código

```bash
git pull && sudo docker compose up -d --build
```

## Limites e cuidados

- Limite por pessoa (IP) por dia nas ações com IA: `LIMITE_RESUMOS_DIA` e `LIMITE_BUSCAS_DIA` no `.env`.
- O uvicorn roda com `--proxy-headers` para enxergar o IP real atrás do Caddy; sem isso, todos dividiriam o mesmo limite.
- O Phoenix (tracing) não roda na VM, para economizar memória; use localmente.
- A Oracle pode recolher VMs Always Free ociosas. Se acontecer, crie outra e rode os passos de novo: o banco se refaz com o sync.
