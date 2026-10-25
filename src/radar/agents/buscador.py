from __future__ import annotations

import json
import logging
from typing import Any

from radar import db, escopo
from radar.agents import ferramentas
from radar.agents.llm import chat_json
from radar.pncp.models import PerfilEmpresa
from radar.tracing import registrar_saida, span

log = logging.getLogger("radar.buscador")

CANDIDATOS = 50
LOTE_TRIAGEM = 25
TAMANHO_OBJETO = 300

SISTEMA_PLANO = """Você traduz pedidos de donos de pequenas empresas em parâmetros de busca de licitações.
Responda SOMENTE um JSON com as chaves:
- "uf": sigla do estado (ex. "SP")
- "abrangencia": "regiao" (padrão: Campinas e região, também quando a pergunta só cita Campinas),
   "municipio" (a pergunta pede UMA cidade específica, ex. "só em Valinhos") ou
   "estado" (a pergunta pede o estado todo ou "qualquer cidade")
- "municipio": nome da cidade quando abrangencia = "municipio", senão null
- "palavras_chave": lista de 6 a 10 termos curtos que aparecem no objeto de compras desse segmento,
   incluindo sinônimos e nomes usados pelo setor público
   (ex. limpeza -> "limpeza", "conservação", "asseio", "higienização", "zeladoria", "facilities",
   "serviços gerais", "mão de obra"). Evite termos genéricos que puxam outros segmentos
   (ex.: "manutenção" para uma empresa de limpeza)
- "dias_ate_encerrar": inteiro de 1 a 130; 130 se o pedido não disser prazo
Use o perfil da empresa para preencher o que a pergunta não disser."""

SISTEMA_TRIAGEM = """Você faz a triagem de licitações para uma pequena empresa prestadora de serviço.
Para cada item, decida se o OBJETO é uma contratação que essa empresa poderia executar como atividade principal.
Marque false quando:
- for compra de produtos/materiais (a empresa presta serviço, não revende), salvo se o perfil disser o contrário;
- o serviço do segmento for só uma parte acessória de outra coisa (ex. "limpeza do local" ao fim de uma obra,
  "limpeza de poços" dentro de manutenção hidráulica);
- o objeto for de atividade que o perfil lista em "nao_faz".
Responda SOMENTE um JSON: {"itens": [{"id": "<id>", "aderente": true|false, "motivo": "<até 15 palavras>"}]}
Inclua todos os ids recebidos."""


def planejar(pergunta: str, perfil: PerfilEmpresa) -> dict[str, Any]:
    usuario = f"Perfil:\n{perfil.model_dump_json(indent=2)}\n\nPergunta: {pergunta}"
    with span("planejar", entrada=pergunta) as s:
        plano = chat_json("groq", SISTEMA_PLANO, usuario)
        registrar_saida(s, plano)
    return plano


def triar(candidatos: list[dict[str, Any]], perfil: PerfilEmpresa) -> list[dict[str, Any]]:
    perfil_curto = perfil.model_dump_json(include={"segmento", "palavras_chave", "nao_faz"})
    vereditos: dict[str, dict[str, Any]] = {}
    with span("triagem", entrada={"candidatos": len(candidatos)}) as s:
        for i in range(0, len(candidatos), LOTE_TRIAGEM):
            lote = [
                {"id": c["numero_controle"], "objeto": " ".join(c.get("objeto", "").split())[:TAMANHO_OBJETO]}
                for c in candidatos[i : i + LOTE_TRIAGEM]
            ]
            usuario = f"Perfil: {perfil_curto}\n\nItens:\n{json.dumps(lote, ensure_ascii=False)}"
            resposta = chat_json("groq", SISTEMA_TRIAGEM, usuario)
            vereditos.update({v["id"]: v for v in resposta.get("itens", []) if "id" in v})
        registrar_saida(s, {"aderentes": sum(v.get("aderente") is True for v in vereditos.values())})

    aderentes = []
    for c in candidatos:
        v = vereditos.get(c["numero_controle"])
        if v and v.get("aderente") is True:
            aderentes.append({**c, "motivo_triagem": v.get("motivo", "")})
        else:
            log.info("triagem descartou %s: %s", c["numero_controle"], (v or {}).get("motivo", "sem veredito"))
    return aderentes


def _dentro_da_faixa(r: dict[str, Any], perfil: PerfilEmpresa) -> bool:
    valor = r.get("valor_estimado")
    if valor is None or not perfil.faixa_valor_max:
        return True
    return valor <= perfil.faixa_valor_max * 1.5


def _municipios(params: dict[str, Any], uf: str) -> str | list[str] | None:
    abrangencia = params.get("abrangencia") or "regiao"
    if abrangencia == "estado":
        return None
    if abrangencia == "municipio" and params.get("municipio"):
        with db.conectar() as con:
            codigo = db.codigo_por_municipio(con, params["municipio"], uf)
        if codigo:
            return codigo
        log.warning("Município %r sem licitações no banco; usando a região", params["municipio"])
    return list(escopo.REGIAO)


def buscar(
    pergunta: str, perfil: PerfilEmpresa, limite: int = 10, detalhes: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    with span("buscador", entrada={"pergunta": pergunta}, tipo="AGENT") as s:
        params = planejar(pergunta, perfil)
        uf = params.get("uf") or perfil.uf
        filtro = {
            "uf": uf,
            "palavras_chave": params.get("palavras_chave") or perfil.palavras_chave,
            "codigo_municipio_ibge": _municipios(params, uf),
            "dias_ate_encerrar": int(params.get("dias_ate_encerrar") or escopo.DIAS_MAX),
            "limite": CANDIDATOS,
        }
        with span("buscar_licitacoes", entrada=filtro, tipo="TOOL") as t:
            candidatos = ferramentas.buscar_licitacoes(**filtro)
            registrar_saida(t, {"candidatos": len(candidatos)})
        na_faixa = [c for c in candidatos if _dentro_da_faixa(c, perfil)]
        aderentes = triar(na_faixa, perfil) if na_faixa else []

        resumo = {
            "params": params,
            "candidatos": len(candidatos),
            "fora_da_faixa": len(candidatos) - len(na_faixa),
            "descartados_triagem": len(na_faixa) - len(aderentes),
            "aderentes": [a["numero_controle"] for a in aderentes],
        }
        registrar_saida(s, resumo)
        if detalhes is not None:
            detalhes.update(resumo)
        return aderentes[:limite]


PERGUNTA_FEED_REGIAO = "Quais licitações abertas em Campinas e região servem para o meu segmento?"
PERGUNTA_FEED_ESTADO = "Quais licitações abertas em qualquer cidade do estado servem para o meu segmento?"


def feed(perfil: PerfilEmpresa) -> dict[str, Any]:
    det_regiao: dict[str, Any] = {}
    det_estado: dict[str, Any] = {}
    regiao = buscar(PERGUNTA_FEED_REGIAO, perfil, limite=CANDIDATOS, detalhes=det_regiao)
    na_regiao = {r["numero_controle"] for r in regiao}
    estado = [
        e for e in buscar(PERGUNTA_FEED_ESTADO, perfil, limite=CANDIDATOS, detalhes=det_estado)
        if e["numero_controle"] not in na_regiao
    ]
    return {"regiao": regiao, "estado": estado, "detalhes": {"regiao": det_regiao, "estado": det_estado}}


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    perfil = PerfilEmpresa.model_validate_json(Path("data/perfil_exemplo.json").read_text(encoding="utf-8"))
    pergunta = " ".join(sys.argv[1:]) or "tem licitação de limpeza aberta em Campinas?"
    print(json.dumps(buscar(pergunta, perfil), ensure_ascii=False, indent=2))
