from __future__ import annotations

import hashlib
import os
from datetime import date

from radar import db

def limites() -> dict[str, int]:
    return {
        "resumo": int(os.getenv("LIMITE_RESUMOS_DIA", "10")),
        "busca": int(os.getenv("LIMITE_BUSCAS_DIA", "15")),
    }


def chave_do_ip(ip: str | None) -> str:
    return hashlib.sha256((ip or "desconhecido").encode()).hexdigest()[:16]


def situacao(chave: str) -> dict[str, dict[str, int]]:
    with db.conectar() as con:
        usados = db.uso_do_dia(con, chave, date.today().isoformat())
    return {tipo: {"usados": usados.get(tipo, 0), "limite": limite} for tipo, limite in limites().items()}


def esgotado(chave: str, tipo: str) -> bool:
    s = situacao(chave)[tipo]
    return s["usados"] >= s["limite"]


def consumir(chave: str, tipo: str) -> None:
    with db.conectar() as con:
        db.registrar_uso(con, chave, date.today().isoformat(), tipo)
