import json

import httpx

from radar import erros


def _status_error(codigo: int) -> httpx.HTTPStatusError:
    req = httpx.Request("GET", "https://pncp.gov.br/x")
    return httpx.HTTPStatusError("erro", request=req, response=httpx.Response(codigo, request=req))


class _LimiteGroq(Exception):
    status_code = 429


_LimiteGroq.__module__ = "groq._exceptions"


def test_nenhuma_mensagem_expoe_detalhe_tecnico():
    casos = [
        _status_error(422),
        httpx.ConnectError("falhou"),
        httpx.ReadTimeout("lento"),
        FileNotFoundError("Nenhum arquivo de edital em 1-1-1/2026"),
        ValueError("Edital com mais de 60 MB; abra pelo link do PNCP."),
        ValueError("Sem dados de SP: o escopo atual cobre só SP."),
        json.JSONDecodeError("x", "doc", 0),
        _LimiteGroq("429 Too Many Requests"),
        RuntimeError("qualquer coisa"),
    ]
    for exc in casos:
        texto = erros.mensagem(exc)
        assert "http" not in texto.lower() and "python" not in texto.lower(), texto
        assert texto.endswith("."), texto


def test_casos_especificos():
    assert erros.mensagem(_status_error(422)) == erros.PNCP_FORA
    assert "Não encontramos" in erros.mensagem(_status_error(404))
    assert erros.mensagem(httpx.ReadTimeout("lento")) == erros.PNCP_LENTO
    assert erros.mensagem(_LimiteGroq("rate")) == erros.LIMITE_IA
    assert erros.mensagem(RuntimeError("x")) == erros.GENERICO
