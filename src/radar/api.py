from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime, timedelta
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from radar import db, escopo, limites
from radar.agents import ferramentas
from radar.agents.buscador import buscar, feed
from radar.agents.judge import julgar
from radar.agents.leitor import ler
from radar.pncp.client import RAIZ
from radar.pncp.models import PerfilEmpresa
from radar.tracing import registrar_saida, setup_tracing, span

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
log = logging.getLogger("radar.api")

PERFIL_PADRAO = RAIZ / "data" / "perfil_exemplo.json"
FRONTEND_DIST = RAIZ / "frontend" / "dist"

setup_tracing()
app = FastAPI(title="Radar de Licitações")


class PedidoBusca(BaseModel):
    pergunta: str
    perfil: PerfilEmpresa


class PedidoAvaliacao(BaseModel):
    numero_controle: str
    perfil: PerfilEmpresa | None = None


def _anotar(itens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    with db.conectar() as con:
        resumos = db.resumos_itens(con, [i["numero_controle"] for i in itens])
    for item in itens:
        r = resumos.get(item["numero_controle"])
        if r:
            item["tipo_objeto"], item["me_epp"] = r["tipo_objeto"], r["me_epp"]
    return itens


@app.get("/api/status")
def status() -> dict[str, Any]:
    with db.conectar() as con:
        sync = db.ultimo_sync(con, escopo.UF)
        verificadas = db.contar_resumos_itens(con, escopo.UF)
    escopo_info = {
        "uf": escopo.UF, "regiao": escopo.REGIAO_NOME, "municipios": len(escopo.REGIAO), "dias_max": escopo.DIAS_MAX,
    }
    if sync is None:
        return {"escopo": escopo_info, "banco": None}
    quando = datetime.fromisoformat(sync["executado_em"].split("#")[0])
    return {
        "escopo": escopo_info,
        "banco": {"total": sync["total"], "ultimo_sync": quando.isoformat(), "desatualizado": (datetime.now() - quando).days >= 1,
                  "itens_verificados": verificadas},
    }


@app.get("/api/health")
def health() -> dict[str, Any]:
    with db.conectar() as con:
        sync = db.ultimo_sync(con, escopo.UF)
    if sync is None:
        raise HTTPException(status_code=503, detail="Banco vazio: rode python -m radar.sync")
    return {"ok": True, "licitacoes": sync["total"], "ultimo_sync": sync["executado_em"].split("#")[0]}


@app.get("/api/perfil")
def perfil_exemplo() -> PerfilEmpresa:
    return PerfilEmpresa.model_validate(json.loads(PERFIL_PADRAO.read_text(encoding="utf-8")))


@app.get("/api/licitacoes")
def listar_licitacoes(
    pagina: int = Query(1, ge=1),
    tamanho: int = Query(20, ge=1, le=50),
    q: str = "",
    abrangencia: str = Query("estado", pattern="^(estado|regiao|municipio)$"),
    municipio: str | None = None,
    dias: int | None = Query(None, ge=1, le=escopo.DIAS_MAX),
    me_epp: bool = False,
) -> dict[str, Any]:
    codigos = None
    if abrangencia == "regiao":
        codigos = list(escopo.REGIAO)
    elif abrangencia == "municipio" and municipio:
        codigos = [municipio]
    with db.conectar() as con:
        itens, total = db.listar(
            con, escopo.UF, pagina, tamanho, q, codigos,
            datetime.now() + timedelta(days=dias) if dias else None, so_me_epp=me_epp,
        )
    return {
        "itens": _anotar([i.resumo_curto() for i in itens]),
        "total": total,
        "pagina": pagina,
        "paginas": max(1, -(-total // tamanho)),
    }


@app.get("/api/municipios")
def listar_municipios() -> list[dict[str, Any]]:
    with db.conectar() as con:
        return db.municipios(con, escopo.UF)


class PedidoFeed(BaseModel):
    perfil: PerfilEmpresa


MENSAGEM_LIMITE = {
    "busca": "Você usou as {limite} buscas com IA de hoje. A lista de todas as licitações e a busca por texto continuam liberadas.",
    "resumo": "Você usou os {limite} resumos com IA de hoje. Resumos que já foram feitos antes continuam liberados.",
}


def _checar(request: Request, tipo: str) -> str:
    chave = limites.chave_do_ip(request.client.host if request.client else None)
    if limites.esgotado(chave, tipo):
        limite = limites.limites()[tipo]
        raise HTTPException(status_code=429, detail=MENSAGEM_LIMITE[tipo].format(limite=limite) + " O limite volta à meia-noite.")
    return chave


@app.get("/api/uso")
def uso(request: Request) -> dict[str, Any]:
    return limites.situacao(limites.chave_do_ip(request.client.host if request.client else None))


@app.post("/api/feed")
def feed_inicial(pedido: PedidoFeed) -> dict[str, Any]:
    try:
        with span("feed", entrada={"segmento": pedido.perfil.segmento}) as s:
            resultado = feed(pedido.perfil)
            registrar_saida(s, {"regiao": len(resultado["regiao"]), "estado": len(resultado["estado"])})
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _anotar(resultado["regiao"])
    _anotar(resultado["estado"])
    return {**resultado, "regiao_nome": escopo.REGIAO_NOME}


@app.post("/api/buscar")
def buscar_licitacoes(pedido: PedidoBusca, request: Request) -> dict[str, Any]:
    chave = _checar(request, "busca")
    detalhes: dict[str, Any] = {}
    try:
        with span("busca", entrada=pedido.pergunta) as s:
            candidatas = buscar(pedido.pergunta, pedido.perfil, limite=50, detalhes=detalhes)
            registrar_saida(s, {"aderentes": len(candidatas)})
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    limites.consumir(chave, "busca")
    return {"candidatas": _anotar(candidatas), "detalhes": detalhes, "uso": limites.situacao(chave)}


@app.post("/api/avaliar")
def avaliar(pedido: PedidoAvaliacao, request: Request) -> dict[str, Any]:
    chave = _checar(request, "resumo")
    numero = pedido.numero_controle
    tempos: dict[str, Any] = {}
    try:
        with span("avaliar_edital", entrada=numero) as raiz:
            t = time.perf_counter()
            with span("baixar_edital", entrada=numero, tipo="TOOL") as s:
                detalhe = ferramentas.detalhar_licitacao(numero)
                pdf = ferramentas.baixar_edital_pdf(numero)
                registrar_saida(s, {"arquivo": pdf.name, "mb": round(pdf.stat().st_size / 1e6, 1)})
            tempos["download_s"] = round(time.perf_counter() - t, 1)
            tempos["pdf_mb"] = round(pdf.stat().st_size / 1e6, 1)
            t = time.perf_counter()
            ficha = ler(pdf, tempos=tempos)
            tempos["leitor_s"] = round(time.perf_counter() - t, 1)
            t = time.perf_counter()
            veredito = julgar(pedido.perfil, ficha) if pedido.perfil else None
            tempos["judge_s"] = round(time.perf_counter() - t, 1)
            registrar_saida(raiz, {"aderencia": veredito.aderencia if veredito else None, "tempos": tempos})
    except Exception as exc:
        log.warning("Falha ao avaliar %s: %s", numero, exc)
        raise HTTPException(status_code=502, detail=f"Não consegui ler o edital: {exc}") from exc
    log.info("avaliar %s: %s", numero, tempos)
    if not tempos.get("cache"):
        limites.consumir(chave, "resumo")

    arquivos = detalhe["arquivos"]
    edital = next((a for a in arquivos if "edital" in (a.get("tipo") or "").lower()), arquivos[0] if arquivos else {})
    return {
        "ficha": ficha.model_dump(), "veredito": veredito.model_dump() if veredito else None, "url_edital": edital.get("url"), "tempos": tempos,
        "uso": limites.situacao(chave),
    }


if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
