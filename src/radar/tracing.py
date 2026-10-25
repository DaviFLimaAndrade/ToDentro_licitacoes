from __future__ import annotations

import json
import logging
import os
from contextlib import contextmanager
from typing import Any, Iterator, Literal

log = logging.getLogger(__name__)
_tracer = None

Tipo = Literal["CHAIN", "AGENT", "LLM", "TOOL"]


def setup_tracing(projeto: str = "radar-licitacoes") -> None:
    global _tracer
    if _tracer is not None:
        return
    try:
        from opentelemetry import trace
        from phoenix.otel import register
    except ImportError:
        log.info("Phoenix não instalado; tracing desligado.")
        return
    for var in ("NO_PROXY", "no_proxy"):
        atual = os.environ.get(var, "")
        if "localhost" not in atual:
            os.environ[var] = ",".join(filter(None, [atual, "localhost", "127.0.0.1"]))
    base = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006").rstrip("/")
    register(project_name=projeto, endpoint=f"{base}/v1/traces", protocol="http/protobuf", batch=True)
    _tracer = trace.get_tracer("radar")


@contextmanager
def span(nome: str, entrada: Any = None, tipo: Tipo = "CHAIN", **atributos: Any) -> Iterator[Any]:
    if _tracer is None:
        yield _SpanNulo()
        return
    with _tracer.start_as_current_span(nome) as s:
        s.set_attribute("openinference.span.kind", tipo)
        if entrada is not None:
            s.set_attribute("input.value", _json(entrada))
        for chave, valor in atributos.items():
            if valor is not None:
                s.set_attribute(chave, valor)
        yield s


def registrar_saida(s: Any, saida: Any) -> None:
    s.set_attribute("output.value", _json(saida))


def _json(valor: Any) -> str:
    texto = valor if isinstance(valor, str) else json.dumps(valor, ensure_ascii=False, default=str)
    return texto[:8000]


class _SpanNulo:
    def set_attribute(self, *_: Any) -> None:
        pass
