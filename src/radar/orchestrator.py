from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

from radar.agents import ferramentas
from radar.agents.buscador import buscar
from radar.agents.judge import julgar
from radar.agents.leitor import ler
from radar.pncp.models import PerfilEmpresa
from radar.tracing import setup_tracing

log = logging.getLogger("radar.orchestrator")

ORDEM_ADERENCIA = {"alta": 0, "media": 1, "baixa": 2}


def responder(pergunta: str, perfil: PerfilEmpresa, max_editais: int = 3) -> dict[str, Any]:
    candidatas = buscar(pergunta, perfil)
    avaliadas: list[dict[str, Any]] = []

    for licitacao in candidatas[:max_editais]:
        try:
            pdf = ferramentas.baixar_edital_pdf(licitacao["numero_controle"])
            ficha = ler(pdf)
            veredito = julgar(perfil, ficha)
            avaliadas.append({"licitacao": licitacao, "ficha": ficha.model_dump(), "veredito": veredito.model_dump()})
        except Exception as exc:
            log.warning("Falha em %s: %s", licitacao.get("numero_controle"), exc)

    avaliadas.sort(key=lambda a: ORDEM_ADERENCIA[a["veredito"]["aderencia"]])
    return {
        "pergunta": pergunta,
        "encontradas": len(candidatas),
        "avaliadas": avaliadas,
        "nao_avaliadas": candidatas[max_editais:],
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    setup_tracing()
    perfil = PerfilEmpresa.model_validate_json(Path("data/perfil_exemplo.json").read_text(encoding="utf-8"))
    pergunta = " ".join(sys.argv[1:]) or "tem licitação de limpeza aberta em Campinas?"
    print(json.dumps(responder(pergunta, perfil), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
