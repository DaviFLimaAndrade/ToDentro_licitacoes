from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from radar.db import normalizar

TipoObjeto = Literal["servico", "material", "misto"]
BeneficioMeEpp = Literal["exclusiva", "parcial"]


class ResumoItens(BaseModel):
    n_itens: int
    tipo_objeto: TipoObjeto | None = None
    me_epp: BeneficioMeEpp | None = None


def _valor(item: dict[str, Any]) -> float:
    return float(item.get("valorTotal") or 0) or float(item.get("valorUnitarioEstimado") or 0) or 1.0


def resumir(itens: list[dict[str, Any]]) -> ResumoItens:
    if not itens:
        return ResumoItens(n_itens=0)

    tipos = {i.get("materialOuServico") for i in itens} - {None}
    tipo: TipoObjeto | None = None
    if tipos == {"S"}:
        tipo = "servico"
    elif tipos == {"M"}:
        tipo = "material"
    elif tipos:
        tipo = "misto"

    nomes = [normalizar(i.get("tipoBeneficioNome") or "") for i in itens]
    exclusivos = sum("exclusiva" in n for n in nomes)
    com_beneficio = sum(("exclusiva" in n) or ("cota" in n) or ("subcontrata" in n) for n in nomes)
    me_epp: BeneficioMeEpp | None = None
    if exclusivos == len(itens):
        me_epp = "exclusiva"
    elif com_beneficio:
        me_epp = "parcial"

    return ResumoItens(n_itens=len(itens), tipo_objeto=tipo, me_epp=me_epp)


def fracao_valor(itens: list[dict[str, Any]], condicao: Any) -> float:
    total = sum(_valor(i) for i in itens)
    return sum(_valor(i) for i in itens if condicao(i)) / total if total else 0.0
