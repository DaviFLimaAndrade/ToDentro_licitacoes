from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, timedelta

from radar import db, escopo
from radar.pncp.client import PNCPClient

log = logging.getLogger("radar.sync")


def sincronizar(uf: str = escopo.UF, dias: int = escopo.DIAS_MAX) -> int:
    uf = uf.upper()
    sync_id = db.novo_sync_id()
    client = PNCPClient(usar_cache=False)
    con = db.conectar()
    paginas = client.paginas_abertas(data_final=date.today() + timedelta(days=dias), uf=uf)
    for licitacoes in paginas:
        validas = [l for l in licitacoes if not l.uf or l.uf.upper() == uf]
        if len(validas) < len(licitacoes):
            log.warning("%d itens fora de %s descartados", len(licitacoes) - len(validas), uf)
        db.gravar_pagina(con, validas, sync_id)

    total = db.finalizar_sync(con, uf, sync_id)
    log.info("sync %s completo: %d licitações no banco", uf, total)
    return total


def main() -> None:
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uf", default=escopo.UF)
    parser.add_argument("--dias", type=int, default=escopo.DIAS_MAX,
                        help="encerramento até daqui a N dias")
    args = parser.parse_args()
    sincronizar(args.uf, args.dias)


if __name__ == "__main__":
    main()
