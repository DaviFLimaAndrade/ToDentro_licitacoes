from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from radar.pncp.client import CACHE_DIR, RAIZ
from radar.tracing import registrar_saida, span

load_dotenv(RAIZ / ".env")

Provedor = Literal["groq", "gemini"]
LLM_CACHE = CACHE_DIR / "llm"


def _cache_path(provedor: str, sistema: str, usuario: str) -> Any:
    chave = hashlib.sha256(f"{provedor}|{sistema}|{usuario}".encode()).hexdigest()[:24]
    return LLM_CACHE / f"{chave}.json"


@retry(wait=wait_exponential(multiplier=2, min=4, max=60), stop=stop_after_attempt(5), reraise=True)
def _chamar_groq(sistema: str, usuario: str, tempos: dict[str, float]) -> str:
    from groq import Groq

    client = Groq(api_key=os.environ["GROQ_API_KEY"], timeout=60.0)
    resp = client.chat.completions.create(
        model=_modelo("groq"),
        messages=[{"role": "system", "content": sistema}, {"role": "user", "content": usuario}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    if resp.usage is not None:
        tempos["tokens_entrada"] = resp.usage.prompt_tokens or 0
        tempos["tokens_saida"] = resp.usage.completion_tokens or 0
    return resp.choices[0].message.content or "{}"


def _modelo(provedor: str) -> str:
    if provedor == "groq":
        return os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    return os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def _fechar_span(s: Any, dados: dict[str, Any], tempos: dict[str, float]) -> None:
    registrar_saida(s, dados)
    s.set_attribute("llm.cache", bool(tempos.get("cache")))
    if "tokens_entrada" in tempos:
        s.set_attribute("llm.token_count.prompt", int(tempos["tokens_entrada"]))
    if "tokens_saida" in tempos:
        s.set_attribute("llm.token_count.completion", int(tempos["tokens_saida"]))


INLINE_MAX_BYTES = 18_000_000


def _config_gemini(sistema: str) -> dict[str, Any]:
    return {
        "system_instruction": sistema,
        "response_mime_type": "application/json",
        "temperature": 0,
        "thinking_config": {"thinking_budget": int(os.getenv("GEMINI_THINKING_BUDGET", "0"))},
    }


def _registrar_uso(resp: Any, tempos: dict[str, float]) -> None:
    uso = resp.usage_metadata
    if uso is not None:
        tempos["tokens_entrada"] = uso.prompt_token_count or 0
        tempos["tokens_saida"] = uso.candidates_token_count or 0


@retry(wait=wait_exponential(multiplier=2, min=4, max=60), stop=stop_after_attempt(5), reraise=True)
def _chamar_gemini(sistema: str, usuario: str, tempos: dict[str, float]) -> str:
    from google import genai

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"], http_options={"timeout": 180_000})
    t = time.perf_counter()
    resp = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"), contents=usuario, config=_config_gemini(sistema)
    )
    tempos["geracao_s"] = round(time.perf_counter() - t, 1)
    _registrar_uso(resp, tempos)
    return resp.text or "{}"


@retry(wait=wait_exponential(multiplier=2, min=4, max=60), stop=stop_after_attempt(5), reraise=True)
def _chamar_gemini_pdf(sistema: str, caminho: Path, instrucao: str, tempos: dict[str, float]) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"], http_options={"timeout": 180_000})
    modelo = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    arquivo = None
    t = time.perf_counter()
    if caminho.stat().st_size <= INLINE_MAX_BYTES:
        parte: Any = types.Part.from_bytes(data=caminho.read_bytes(), mime_type="application/pdf")
    else:
        arquivo = parte = client.files.upload(file=caminho, config={"mime_type": "application/pdf"})
        tempos["upload_s"] = round(time.perf_counter() - t, 1)
    try:
        t = time.perf_counter()
        resp = client.models.generate_content(model=modelo, contents=[parte, instrucao], config=_config_gemini(sistema))
        tempos["geracao_s"] = round(time.perf_counter() - t, 1)
        _registrar_uso(resp, tempos)
    finally:
        if arquivo is not None:
            client.files.delete(name=arquivo.name)
    return resp.text or "{}"


def pdf_json(
    sistema: str, caminho: Path, instrucao: str, usar_cache: bool = True, tempos: dict[str, float] | None = None
) -> dict[str, Any]:
    tempos = tempos if tempos is not None else {}
    LLM_CACHE.mkdir(parents=True, exist_ok=True)
    hash_pdf = hashlib.sha256(caminho.read_bytes()).hexdigest()
    cache = _cache_path("gemini-pdf", sistema, hash_pdf + instrucao)
    mb = round(caminho.stat().st_size / 1e6, 1)
    with span("gemini (pdf)", entrada=f"{instrucao} [{caminho.name}, {mb} MB]", tipo="LLM",
              **{"llm.model_name": _modelo("gemini"), "llm.provider": "google"}) as s:
        if usar_cache and cache.exists():
            tempos["cache"] = 1
            dados = json.loads(cache.read_text(encoding="utf-8"))
        else:
            dados = json.loads(_chamar_gemini_pdf(sistema, caminho, instrucao, tempos))
            if usar_cache:
                cache.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
        _fechar_span(s, dados, tempos)
    return dados


def chat_json(
    provedor: Provedor, sistema: str, usuario: str, usar_cache: bool = True, tempos: dict[str, float] | None = None
) -> dict[str, Any]:
    tempos = tempos if tempos is not None else {}
    LLM_CACHE.mkdir(parents=True, exist_ok=True)
    caminho = _cache_path(provedor, sistema, usuario)
    with span(provedor, entrada=usuario, tipo="LLM",
              **{"llm.model_name": _modelo(provedor), "llm.provider": "groq" if provedor == "groq" else "google"}) as s:
        if usar_cache and caminho.exists():
            tempos["cache"] = 1
            dados = json.loads(caminho.read_text(encoding="utf-8"))
        else:
            chamar = _chamar_groq if provedor == "groq" else _chamar_gemini
            dados = json.loads(chamar(sistema, usuario, tempos))
            if usar_cache:
                caminho.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
        _fechar_span(s, dados, tempos)
    return dados
