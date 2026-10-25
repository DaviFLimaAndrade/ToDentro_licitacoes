"""Servidor MCP (stdio). Nunca use print aqui: stdout é o canal do protocolo; use logging."""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

from radar import db, escopo
from radar.db import normalizar
from radar.parsing import ler_pdf, parece_escaneado
from radar.pncp.client import PNCPClient

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
log = logging.getLogger("radar.mcp")

LIMITE_TEXTO_EDITAL = 20_000

_client = PNCPClient()


def buscar_licitacoes(
    uf: str,
    palavras_chave: list[str],
    codigo_municipio_ibge: str | int | list[str] | None = None,
    dias_ate_encerrar: int = escopo.DIAS_MAX,
    limite: int = 10,
) -> list[dict[str, Any]]:
    """Busca licitações com proposta aberta no PNCP (no banco local, atualizado por radar.sync).

    Escopo do banco: só SP, só abertas para proposta, encerrando em até 130 dias.

    Args:
        uf: sigla do estado. Hoje só "SP" tem dados.
        palavras_chave: termos do objeto da compra; inclua sinônimos, ex. ["limpeza", "zeladoria", "asseio"].
        codigo_municipio_ibge: código IBGE do município (Campinas = "3509502") ou lista de códigos.
            Use "regiao" para Campinas e região (20 municípios da RMC). Opcional.
        dias_ate_encerrar: considera licitações que encerram até daqui a N dias (máximo 130).
        limite: máximo de resultados devolvidos.
    """
    uf = uf.upper()
    dias_ate_encerrar = min(dias_ate_encerrar, escopo.DIAS_MAX)
    with db.conectar() as con:
        sync = db.ultimo_sync(con, uf)
        if sync is None:
            raise ValueError(
                f"Sem dados de {uf}: o escopo atual cobre só {escopo.UF}. "
                f"Para incluir, rode: python -m radar.sync --uf {uf}"
            )
        ibge: str | list[str] | None
        if codigo_municipio_ibge == "regiao":
            ibge = list(escopo.REGIAO)
        elif isinstance(codigo_municipio_ibge, list):
            ibge = [str(c) for c in codigo_municipio_ibge]
        else:
            ibge = str(codigo_municipio_ibge) if codigo_municipio_ibge is not None else None
        encontradas = db.buscar(
            con, uf, palavras_chave,
            encerra_ate=datetime.now() + timedelta(days=dias_ate_encerrar),
            codigo_ibge=ibge, limite=limite,
        )

    log.info("buscar_licitacoes: %d no banco (sync de %s)", len(encontradas), sync["executado_em"])
    return [l.resumo_curto() for l in encontradas]


def detalhar_licitacao(numero_controle: str) -> dict[str, Any]:
    """Dados completos de uma licitação e a lista de arquivos do edital.

    Args:
        numero_controle: o numero_controle devolvido por buscar_licitacoes.
    """
    detalhe = _client.detalhar(numero_controle)
    arquivos = _client.listar_arquivos(numero_controle)
    return {
        "detalhe": detalhe,
        "arquivos": [a.model_dump(exclude_none=True) for a in arquivos],
    }


def baixar_edital_pdf(numero_controle: str) -> Path:
    arquivos = _client.listar_arquivos(numero_controle)
    if not arquivos:
        raise FileNotFoundError(f"Nenhum arquivo de edital em {numero_controle}")
    edital = next(
        (a for a in arquivos if "edital" in normalizar(f"{a.tipo or ''} {a.titulo}")),
        arquivos[0],
    )
    return _client.baixar_arquivo(edital.url, numero_controle.replace("/", "_"))


def baixar_edital(numero_controle: str) -> str:
    """Baixa o edital de uma licitação e devolve o texto extraído (truncado).

    Args:
        numero_controle: o numero_controle devolvido por buscar_licitacoes.
    """
    try:
        caminho = baixar_edital_pdf(numero_controle)
    except FileNotFoundError:
        return "Nenhum arquivo de edital encontrado para esta licitação."

    texto, paginas = ler_pdf(caminho)
    if parece_escaneado(texto, paginas):
        return (
            "O edital é um PDF escaneado (imagem), sem texto extraível. "
            f"Arquivo salvo em: {caminho}. Use o link do edital em detalhar_licitacao para abrir."
        )
    if len(texto) > LIMITE_TEXTO_EDITAL:
        texto = texto[:LIMITE_TEXTO_EDITAL] + "\n\n[... edital truncado ...]"
    return texto


mcp = MCPServer("radar-licitacoes")
mcp.tool()(buscar_licitacoes)
mcp.tool()(detalhar_licitacao)
mcp.tool()(baixar_edital)


if __name__ == "__main__":
    mcp.run()
