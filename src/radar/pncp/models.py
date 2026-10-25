from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Licitacao(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    numero_controle: str = Field(alias="numeroControlePNCP")
    objeto: str = Field(default="", alias="objetoCompra")
    modalidade: str | None = Field(default=None, alias="modalidadeNome")
    valor_estimado: float | None = Field(default=None, alias="valorTotalEstimado")
    data_encerramento: str | None = Field(default=None, alias="dataEncerramentoProposta")
    link_sistema_origem: str | None = Field(default=None, alias="linkSistemaOrigem")
    orgao: str | None = None
    municipio: str | None = None
    codigo_ibge: str | None = None
    uf: str | None = None

    @field_validator("valor_estimado")
    @classmethod
    def _zero_e_nao_informado(cls, v: float | None) -> float | None:
        return v or None

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> Licitacao:
        orgao = (raw.get("orgaoEntidade") or {}).get("razaoSocial")
        unidade = raw.get("unidadeOrgao") or {}
        return cls.model_validate(
            {
                **raw,
                "orgao": orgao,
                "municipio": unidade.get("municipioNome"),
                "codigo_ibge": unidade.get("codigoIbge"),
                "uf": unidade.get("ufSigla"),
            }
        )

    def resumo_curto(self) -> dict[str, Any]:
        return self.model_dump(
            include={"numero_controle", "orgao", "municipio", "uf", "objeto",
                     "modalidade", "valor_estimado", "data_encerramento", "link_sistema_origem"},
            exclude_none=True,
        )


class ArquivoEdital(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    titulo: str = Field(default="", alias="titulo")
    url: str = Field(alias="url")
    tipo: str | None = Field(default=None, alias="tipoDocumentoNome")


class PerfilEmpresa(BaseModel):
    nome: str
    segmento: str
    palavras_chave: list[str]
    uf: str
    municipio: str | None = None
    codigo_municipio_ibge: str | None = None
    faixa_valor_min: float | None = None
    faixa_valor_max: float | None = None
    documentos_que_tem: list[str] = []
    nao_faz: list[str] = []
