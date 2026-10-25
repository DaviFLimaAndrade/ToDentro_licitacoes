from __future__ import annotations

import hashlib
import io
import json
import logging
import re
import time
import zipfile
from datetime import date
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from radar.pncp.models import ArquivoEdital, Licitacao

log = logging.getLogger(__name__)

CONSULTA_BASE = "https://pncp.gov.br/api/consulta"
PNCP_BASE = "https://pncp.gov.br/api/pncp"

RAIZ = Path(__file__).resolve().parents[3]
CACHE_DIR = RAIZ / "data" / "cache"
EDITAIS_DIR = RAIZ / "data" / "editais"
MAX_EDITAL_BYTES = 60_000_000


def _formatar_data(d: date) -> str:
    return d.strftime("%Y%m%d")


def parse_numero_controle(numero: str) -> tuple[str, int, int]:
    cnpj, _, resto = numero.split("-", 2)
    sequencial, ano = resto.split("/")
    return cnpj, int(ano), int(sequencial)


def _deve_repetir(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in {429, 500, 502, 503, 504}
    return False


def _download_deve_repetir(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 422:
        return True
    return _deve_repetir(exc)


class PNCPClient:
    def __init__(self, timeout: float = 30.0, usar_cache: bool = True) -> None:
        self._http = httpx.Client(timeout=timeout, follow_redirects=True)
        self._usar_cache = usar_cache
        CACHE_DIR.mkdir(parents=True, exist_ok=True)


    def _chave_cache(self, url: str, params: dict[str, Any]) -> Path:
        bruto = url + json.dumps(params, sort_keys=True, default=str)
        return CACHE_DIR / f"{hashlib.sha256(bruto.encode()).hexdigest()[:24]}.json"

    @retry(
        retry=retry_if_exception(_deve_repetir),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def _get_http(self, url: str, params: dict[str, Any]) -> Any:
        resp = self._http.get(url, params=params)
        resp.raise_for_status()
        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    def _get(self, url: str, params: dict[str, Any] | None = None) -> Any:
        params = {k: v for k, v in (params or {}).items() if v is not None}
        caminho = self._chave_cache(url, params)
        if self._usar_cache and caminho.exists():
            return json.loads(caminho.read_text(encoding="utf-8"))
        log.info("GET %s %s", url, params)
        dados = self._get_http(url, params)
        if self._usar_cache:
            caminho.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
        return dados


    def paginas_abertas(
        self,
        data_final: date,
        uf: str | None = None,
        codigo_municipio_ibge: str | None = None,
        modalidade: int | None = None,
        pausa: float = 1.0,
    ) -> Iterator[list[Licitacao]]:
        """O Swagger diz tamanhoPagina até 500, mas a API real devolve 400 acima de 50."""
        pagina = 1
        while True:
            itens, restantes = self._pagina_abertas(
                data_final, uf, codigo_municipio_ibge, modalidade, pagina
            )
            log.info("página %d: %d itens, %d restantes", pagina, len(itens), restantes)
            yield itens
            if restantes <= 0 or not itens:
                return
            pagina += 1
            time.sleep(pausa)

    def _pagina_abertas(
        self,
        data_final: date,
        uf: str | None,
        codigo_municipio_ibge: str | None,
        modalidade: int | None,
        pagina: int,
        tamanho_pagina: int = 50,
    ) -> tuple[list[Licitacao], int]:
        dados = self._get(
            f"{CONSULTA_BASE}/v1/contratacoes/proposta",
            {
                "dataFinal": _formatar_data(data_final),
                "uf": uf,
                "codigoMunicipioIbge": codigo_municipio_ibge,
                "codigoModalidadeContratacao": modalidade,
                "pagina": pagina,
                "tamanhoPagina": tamanho_pagina,
            },
        )
        itens = dados.get("data", []) if isinstance(dados, dict) else dados
        licitacoes: list[Licitacao] = []
        for raw in itens or []:
            try:
                licitacoes.append(Licitacao.from_api(raw))
            except Exception:
                log.warning("Item ignorado por dado inválido: %s", raw.get("numeroControlePNCP"))
        restantes = dados.get("paginasRestantes", 0) if isinstance(dados, dict) else 0
        return licitacoes, restantes or 0

    def detalhar(self, numero_controle: str) -> dict[str, Any]:
        cnpj, ano, seq = parse_numero_controle(numero_controle)
        return self._get(f"{CONSULTA_BASE}/v1/orgaos/{cnpj}/compras/{ano}/{seq}")

    def listar_arquivos(self, numero_controle: str) -> list[ArquivoEdital]:
        cnpj, ano, seq = parse_numero_controle(numero_controle)
        dados = self._get(f"{PNCP_BASE}/v1/orgaos/{cnpj}/compras/{ano}/{seq}/arquivos")
        itens = dados if isinstance(dados, list) else dados.get("data", [])
        return [
            ArquivoEdital.model_validate(i)
            for i in itens
            if i.get("url") and i.get("statusAtivo", True)
        ]

    def listar_itens(self, numero_controle: str) -> list[dict[str, Any]]:
        cnpj, ano, seq = parse_numero_controle(numero_controle)
        dados = self._get(
            f"{PNCP_BASE}/v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens", {"pagina": 1, "tamanhoPagina": 500}
        )
        return dados if isinstance(dados, list) else []

    @retry(
        retry=retry_if_exception(_download_deve_repetir),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    def _baixar_com_teto(self, url: str) -> tuple[bytes, str]:
        partes = bytearray()
        with self._http.stream("GET", url, timeout=120.0) as resp:
            for bloco in resp.iter_bytes():
                partes.extend(bloco)
                if len(partes) > MAX_EDITAL_BYTES:
                    raise ValueError(f"Edital com mais de {MAX_EDITAL_BYTES // 1_000_000} MB; abra pelo link do PNCP.")
            conteudo = bytes(partes)
            # O PNCP às vezes responde 422 com o arquivo inteiro e válido no corpo.
            if resp.is_error and conteudo[:4] not in (b"%PDF", b"PK\x03\x04"):
                resp.raise_for_status()
            return conteudo, resp.headers.get("content-disposition", "")

    def baixar_arquivo(self, url: str, nome_base: str) -> Path:
        EDITAIS_DIR.mkdir(parents=True, exist_ok=True)
        pdf = EDITAIS_DIR / f"{nome_base}.pdf"
        if pdf.exists():
            return pdf
        conteudo, disposicao = self._baixar_com_teto(url)
        if _extensao(disposicao, conteudo) != ".zip":
            pdf.write_bytes(conteudo)
            return pdf

        zip_path = EDITAIS_DIR / f"{nome_base}.zip"
        zip_path.write_bytes(conteudo)
        pdfs = _pdfs_do_zip(conteudo)
        if not pdfs:
            raise ValueError(f"Zip do edital sem PDF: {zip_path.name}")
        editais = [p for p in pdfs if "edital" in p[0].lower()]
        _, conteudo = max(editais or pdfs, key=lambda p: len(p[1]))
        pdf.write_bytes(conteudo)
        return pdf


def _pdfs_do_zip(dados: bytes, profundidade: int = 0) -> list[tuple[str, bytes]]:
    achados: list[tuple[str, bytes]] = []
    with zipfile.ZipFile(io.BytesIO(dados)) as zf:
        for info in zf.infolist():
            nome = info.filename.lower()
            if nome.endswith(".pdf"):
                achados.append((info.filename, zf.read(info)))
            elif nome.endswith(".zip") and profundidade < 3:
                achados.extend(_pdfs_do_zip(zf.read(info), profundidade + 1))
    return achados


def _extensao(disposicao: str, conteudo: bytes) -> str:
    achou = re.search(r'filename="?([^";]+)"?', disposicao)
    if achou:
        return Path(achou.group(1)).suffix.lower()
    return ".zip" if conteudo[:2] == b"PK" else ".pdf"
