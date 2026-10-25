from __future__ import annotations

import json

import httpx

LIMITE_IA = "A IA está no limite de uso do plano gratuito agora. Espere um minuto e tente de novo."
PNCP_FORA = "O portal do governo (PNCP) não respondeu agora. Tente de novo em alguns minutos."
PNCP_LENTO = "O portal do governo (PNCP) demorou demais para responder. Tente de novo em alguns minutos."
GENERICO = "Algo deu errado do nosso lado. Tente de novo; se continuar, abra a licitação pelo link do PNCP."


def _status(exc: BaseException) -> int | None:
    for atributo in ("status_code", "code", "status"):
        valor = getattr(exc, atributo, None)
        if isinstance(valor, int):
            return valor
    resposta = getattr(exc, "response", None)
    return getattr(resposta, "status_code", None)


def _e_da_ia(exc: BaseException) -> bool:
    modulo = type(exc).__module__
    return modulo.startswith(("groq", "google"))


def mensagem(exc: BaseException) -> str:
    if isinstance(exc, ValueError) and "Sem dados" in str(exc):
        return "As licitações ainda estão sendo carregadas. Volte em alguns minutos."
    if isinstance(exc, FileNotFoundError):
        return "Esta licitação não tem edital publicado no PNCP. Veja os documentos direto no portal."
    if isinstance(exc, ValueError) and "MB" in str(exc):
        return "O edital é grande demais para ler aqui. Abra pelo link do PNCP."
    if isinstance(exc, ValueError) and "sem PDF" in str(exc):
        return "O edital veio num formato que ainda não conseguimos ler. Abra pelo link do PNCP."
    if isinstance(exc, json.JSONDecodeError):
        return "A IA respondeu num formato inesperado. Tente de novo."
    if _e_da_ia(exc):
        texto = str(exc).upper()
        if _status(exc) == 429 or "RESOURCE_EXHAUSTED" in texto or "RATE" in texto:
            return LIMITE_IA
        return "O serviço de IA falhou agora. Tente de novo em alguns instantes."
    if isinstance(exc, httpx.TimeoutException):
        return PNCP_LENTO
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in (400, 404):
        return "Não encontramos esta licitação no PNCP. Ela pode ter sido cancelada ou retirada do portal."
    if isinstance(exc, (httpx.HTTPStatusError, httpx.TransportError)):
        return PNCP_FORA
    return GENERICO
