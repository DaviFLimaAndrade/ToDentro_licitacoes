from __future__ import annotations

import argparse
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from radar import db, escopo
from radar.itens import resumir
from radar.pncp.client import PNCPClient

log = logging.getLogger("radar.enriquecer")


def enriquecer(limite: int = 500, paralelas: int = 6) -> int:
    client = PNCPClient()
    con = db.conectar()
    pendentes = db.sem_resumo_itens(con, escopo.UF, list(escopo.REGIAO), limite)
    log.info("%d licitações sem resumo dos itens (limite %d, %d em paralelo)", len(pendentes), limite, paralelas)
    feitos = 0
    inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=paralelas) as pool:
        futuros = {pool.submit(client.listar_itens, numero): numero for numero in pendentes}
        for futuro in as_completed(futuros):
            numero = futuros[futuro]
            try:
                resumo = resumir(futuro.result())
            except Exception as exc:
                log.warning("itens de %s: %s", numero, exc)
                continue
            db.gravar_resumo_itens(con, numero, resumo.model_dump())
            feitos += 1
            if feitos % 100 == 0:
                log.info("%d/%d (%.1f por minuto)", feitos, len(pendentes), feitos / (time.perf_counter() - inicio) * 60)
    log.info("enriquecidas %d; total com resumo em %s: %d", feitos, escopo.UF, db.contar_resumos_itens(con, escopo.UF))
    return feitos


def main() -> None:
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limite", type=int, default=500)
    parser.add_argument("--paralelas", type=int, default=6)
    args = parser.parse_args()
    enriquecer(args.limite, args.paralelas)


if __name__ == "__main__":
    main()
