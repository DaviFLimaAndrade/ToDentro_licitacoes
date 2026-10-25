from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

from radar.agents.leitor import FichaEdital
from radar.agents.llm import chat_json
from radar.pncp.models import PerfilEmpresa
from radar.tracing import registrar_saida, span

SISTEMA = """Você avalia se uma licitação vale a pena para uma pequena empresa.
Use SOMENTE o perfil e a ficha do edital recebidos. Avalie quatro critérios:
1. Objeto: o serviço pedido é o que a empresa faz? Algo da lista "nao_faz" pesa contra.
2. Valor: o valor estimado está dentro da faixa da empresa?
3. Exigências: alguma exigência que a empresa provavelmente não tem pode barrar a participação?
4. Prazo: dá tempo de preparar a proposta?

Responda SOMENTE um JSON com as chaves:
- "aderencia": "alta", "media" ou "baixa"
- "vale_a_pena": true ou false
- "motivo": até 2 frases, em português simples, para o dono da empresa
- "bloqueios": lista do que precisa ser confirmado antes de participar (pode ser vazia)
Se faltar informação para um critério, diga isso no motivo em vez de supor."""


class Veredito(BaseModel):
    aderencia: Literal["alta", "media", "baixa"]
    vale_a_pena: bool
    motivo: str
    bloqueios: list[str] = []


def julgar(perfil: PerfilEmpresa, ficha: FichaEdital) -> Veredito:
    entrada = {"perfil": perfil.model_dump(), "ficha": ficha.model_dump()}
    with span("judge", entrada=entrada, tipo="AGENT") as s:
        usuario = (
            f"Hoje: {date.today():%d/%m/%Y}\n\n"
            f"Perfil:\n{perfil.model_dump_json(indent=2)}\n\n"
            f"Ficha do edital:\n{ficha.model_dump_json(indent=2)}"
        )
        veredito = Veredito.model_validate(chat_json("groq", SISTEMA, usuario))
        registrar_saida(s, veredito.model_dump())
        return veredito
