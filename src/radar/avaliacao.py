from __future__ import annotations

import json
import logging
import re
import sys
from datetime import datetime, timedelta
from typing import Any

from radar import db, escopo
from radar.agents.buscador import PERGUNTA_FEED_ESTADO, planejar, triar
from radar.db import normalizar
from radar.itens import fracao_valor
from radar.pncp.client import RAIZ, PNCPClient
from radar.pncp.models import PerfilEmpresa

log = logging.getLogger("radar.avaliacao")

PASTA = RAIZ / "data" / "avaliacao"
POR_ABRANGENCIA = 50

LIMPEZA = re.compile(r"\b(limpeza|asseio|conservacao|higienizacao|zeladoria|servicos gerais|servente|facilities)")
ACESSORIO = re.compile(
    r"caixa d|reservatori|cisterna|\bpoco|enxoval|lavanderia|ar.condicionado|climatiza|fossa|esgot|"
    r"via(s)? publica|urbana|bueiro|galeria|fachada|veicul|frota|desentup|dedetiza|desinsetiza|piscina|"
    r"terreno|rocada|capina|hospitalar"
)


def rotular(itens: list[dict[str, Any]], nao_faz: list[str]) -> tuple[str, str]:
    if not itens:
        return "sem_dados", "compra sem itens no PNCP"
    servicos = [i for i in itens if i.get("materialOuServico") == "S"]
    if not servicos:
        return "nao_serve", "todos os itens são Material (compra, não serviço)"

    desc = lambda i: normalizar(i.get("descricao") or "")
    de_limpeza = [i for i in servicos if LIMPEZA.search(desc(i))]
    if not de_limpeza:
        return "nao_serve", "serviço sem item de limpeza/asseio/conservação"

    proibidos = [normalizar(t) for t in nao_faz]
    if any(ACESSORIO.search(desc(i)) for i in de_limpeza):
        return "ambiguo", "limpeza de outro ramo ou acessória: " + desc(de_limpeza[0])[:80]
    if any(any(p in desc(i) for p in proibidos) for i in servicos):
        return "ambiguo", "mistura com atividade que o perfil não faz"
    fracao = fracao_valor(itens, lambda i: i in de_limpeza)
    if fracao >= 0.5:
        return "serve", f"{fracao:.0%} do valor em serviço de limpeza"
    return "ambiguo", f"limpeza é só {fracao:.0%} do valor"


def montar_conjunto(perfil: PerfilEmpresa) -> list[dict[str, Any]]:
    termos = planejar(PERGUNTA_FEED_ESTADO, perfil).get("palavras_chave") or perfil.palavras_chave
    ate = datetime.now() + timedelta(days=escopo.DIAS_MAX)
    with db.conectar() as con:
        regiao = db.buscar(con, escopo.UF, termos, ate, list(escopo.REGIAO), limite=POR_ABRANGENCIA)
        estado = db.buscar(con, escopo.UF, termos, ate, None, limite=POR_ABRANGENCIA)
    vistos: dict[str, Any] = {}
    for lic in regiao + estado:
        vistos.setdefault(lic.numero_controle, lic)

    client = PNCPClient()
    conjunto = []
    for numero, lic in vistos.items():
        rotulo, motivo = rotular(client.listar_itens(numero), perfil.nao_faz)
        conjunto.append({**lic.resumo_curto(), "rotulo_auto": rotulo, "motivo_rotulo": motivo})
    log.info("conjunto: %d licitações (termos: %s)", len(conjunto), termos)
    return conjunto


def avaliar(perfil: PerfilEmpresa) -> dict[str, Any]:
    PASTA.mkdir(parents=True, exist_ok=True)
    conjunto = montar_conjunto(perfil)

    revisao_path = PASTA / "revisao_manual.json"
    revisao = json.loads(revisao_path.read_text(encoding="utf-8")) if revisao_path.exists() else {}
    for item in conjunto:
        r = revisao.get(item["numero_controle"])
        item["rotulo"] = r["rotulo"] if r else item["rotulo_auto"]
        item["fonte_rotulo"] = "revisão por IA" if r else "itens do PNCP"
        if r:
            item["motivo_rotulo"] = r["motivo"]

    aderentes = {a["numero_controle"]: a.get("motivo_triagem", "") for a in triar(conjunto, perfil)}
    for item in conjunto:
        item["triagem_serve"] = item["numero_controle"] in aderentes
        item["motivo_triagem"] = aderentes.get(item["numero_controle"], "")

    avaliaveis = [i for i in conjunto if i["rotulo"] in ("serve", "nao_serve")]
    vp = sum(i["rotulo"] == "serve" and i["triagem_serve"] for i in avaliaveis)
    fp = sum(i["rotulo"] == "nao_serve" and i["triagem_serve"] for i in avaliaveis)
    fn = sum(i["rotulo"] == "serve" and not i["triagem_serve"] for i in avaliaveis)
    vn = sum(i["rotulo"] == "nao_serve" and not i["triagem_serve"] for i in avaliaveis)
    metricas = {
        "total": len(conjunto),
        "avaliaveis": len(avaliaveis),
        "ambiguos_sem_revisao": sum(i["rotulo"] == "ambiguo" for i in conjunto),
        "sem_dados": sum(i["rotulo"] == "sem_dados" for i in conjunto),
        "vp": vp, "fp": fp, "fn": fn, "vn": vn,
        "precisao": round(vp / (vp + fp), 3) if vp + fp else None,
        "recall": round(vp / (vp + fn), 3) if vp + fn else None,
        "acuracia": round((vp + vn) / len(avaliaveis), 3) if avaliaveis else None,
    }
    (PASTA / "conjunto_triagem.json").write_text(
        json.dumps({"gerado_em": datetime.now().isoformat(timespec="seconds"), "metricas": metricas,
                    "itens": conjunto}, ensure_ascii=False, indent=2), encoding="utf-8")
    (PASTA / "relatorio_triagem.md").write_text(_relatorio(metricas, conjunto), encoding="utf-8")
    return metricas


def _relatorio(m: dict[str, Any], conjunto: list[dict[str, Any]]) -> str:
    pct = lambda v: "—" if v is None else f"{v:.0%}"
    erros = [i for i in conjunto if i["rotulo"] in ("serve", "nao_serve") and (i["rotulo"] == "serve") != i["triagem_serve"]]
    linhas = [
        "# Avaliação da triagem (perfil: limpeza predial)", "",
        f"Gerado em {datetime.now():%d/%m/%Y %H:%M}. Rótulos tirados dos itens da compra no PNCP "
        "(material/serviço e descrição do catálogo); casos ambíguos revisados por IA (não por humano), com motivo. "
        "A triagem só vê o texto do objeto.", "",
        "| Métrica | Valor |", "| --- | --- |",
        f"| Licitações no conjunto | {m['total']} |",
        f"| Avaliáveis (rótulo serve/não serve) | {m['avaliaveis']} |",
        f"| **Precisão** (das que a IA mostrou, quantas servem) | **{pct(m['precisao'])}** |",
        f"| **Recall** (das que servem, quantas a IA mostrou) | **{pct(m['recall'])}** |",
        f"| Acurácia | {pct(m['acuracia'])} |",
        f"| Matriz | VP {m['vp']} · FP {m['fp']} · FN {m['fn']} · VN {m['vn']} |",
        f"| Ambíguos sem revisão / sem dados | {m['ambiguos_sem_revisao']} / {m['sem_dados']} |", "",
        "## Erros da triagem", "",
    ]
    for i in erros:
        tipo = "deixou passar" if i["rotulo"] == "serve" else "mostrou sem servir"
        linhas.append(f"- **{tipo}** · {i['municipio']} · {' '.join(i['objeto'].split())[:140]} "
                      f"— rótulo: {i['motivo_rotulo']}" + (f"; IA: {i['motivo_triagem']}" if i["motivo_triagem"] else ""))
    if not erros:
        linhas.append("Nenhum.")
    return "\n".join(linhas) + "\n"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    perfil = PerfilEmpresa.model_validate_json((RAIZ / "data" / "perfil_exemplo.json").read_text(encoding="utf-8"))
    print(json.dumps(avaliar(perfil), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
