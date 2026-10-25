from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel

from radar.agents.llm import chat_json, pdf_json
from radar.parsing import ler_pdf, parece_escaneado, recortar_paginas
from radar.tracing import registrar_saida, span

MAX_CHARS_TEXTO = 200_000
PAGINAS_ESCANEADO = 30

SISTEMA = """Você extrai fatos de editais de licitação brasileiros. Não opine, não recomende.
Responda SOMENTE um JSON com as chaves:
- "objeto": o que está sendo contratado, em uma frase
- "prazo_proposta": data e hora limite para enviar proposta, como está no edital
- "valor_estimado": número em reais ou null se o edital não informar
- "modalidade": ex. "Pregão eletrônico"
- "vigencia": duração do contrato, ex. "12 meses"
- "exigencias": lista curta das exigências de habilitação (atestados, certidões, balanço, garantias)
- "visita_tecnica": texto curto ou null
- "trecho_fonte": uma frase literal curta do edital que comprove o objeto
Se uma informação não estiver no documento, use null. Nunca invente."""

INSTRUCAO = "Extraia a ficha deste edital."


class FichaEdital(BaseModel):
    objeto: str | None = None
    prazo_proposta: str | None = None
    valor_estimado: float | None = None
    modalidade: str | None = None
    vigencia: str | None = None
    exigencias: list[str] = []
    visita_tecnica: str | None = None
    trecho_fonte: str | None = None


def ler(caminho_pdf: Path, tempos: dict[str, Any] | None = None, usar_cache: bool = True) -> FichaEdital:
    tempos = tempos if tempos is not None else {}
    tamanho_mb = round(caminho_pdf.stat().st_size / 1e6, 1)
    with span("leitor", entrada={"arquivo": caminho_pdf.name, "tamanho_mb": tamanho_mb}, tipo="AGENT") as s:
        texto, paginas = ler_pdf(caminho_pdf)
        if not parece_escaneado(texto, paginas):
            tempos["modo"] = "texto"
            usuario = f"{INSTRUCAO}\n\n{texto[:MAX_CHARS_TEXTO]}"
            dados = chat_json("gemini", SISTEMA, usuario, usar_cache=usar_cache, tempos=tempos)
        else:
            recorte = recortar_paginas(caminho_pdf, PAGINAS_ESCANEADO)
            tempos["modo"] = "pdf"
            tempos["pdf_enviado_mb"] = round(recorte.stat().st_size / 1e6, 1)
            dados = pdf_json(SISTEMA, recorte, INSTRUCAO, usar_cache=usar_cache, tempos=tempos)
        ficha = FichaEdital.model_validate(dados)
        registrar_saida(s, {"ficha": ficha.model_dump(), "tempos": tempos})
        return ficha


if __name__ == "__main__":
    import json
    import logging
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    print(json.dumps(ler(Path(sys.argv[1])).model_dump(), ensure_ascii=False, indent=2))
