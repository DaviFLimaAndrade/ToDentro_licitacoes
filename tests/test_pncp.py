from radar.pncp.client import parse_numero_controle
from radar.pncp.models import Licitacao

RAW_EXEMPLO = {
    "numeroControlePNCP": "46068425000133-1-001135/2026",
    "objetoCompra": "Contratação de empresa para Construção do Novo Prédio de Salas de Aula da FEQ",
    "modalidadeNome": "Concorrência - Eletrônica",
    "valorTotalEstimado": 9189933.70,
    "valorTotalHomologado": None,
    "dataEncerramentoProposta": "2026-10-26T09:00:00",
    "orgaoEntidade": {
        "cnpj": "46068425000133",
        "razaoSocial": "UNIVERSIDADE ESTADUAL DE CAMPINAS",
        "poderId": "E",
        "esferaId": "E",
    },
    "unidadeOrgao": {
        "ufNome": "São Paulo",
        "ufSigla": "SP",
        "municipioNome": "Campinas",
        "nomeUnidade": "ESP-UNIVERSIDADE ESTADUAL DE CAMPINAS",
        "codigoUnidade": "450161",
        "codigoIbge": "3509502",
    },
}


def test_parse_numero_controle():
    assert parse_numero_controle("46068425000133-1-001135/2026") == ("46068425000133", 2026, 1135)


def test_licitacao_from_api_achata_orgao_e_unidade():
    lic = Licitacao.from_api(RAW_EXEMPLO)
    assert lic.orgao == "UNIVERSIDADE ESTADUAL DE CAMPINAS"
    assert lic.municipio == "Campinas"
    assert lic.codigo_ibge == "3509502"
    assert lic.uf == "SP"
    assert lic.valor_estimado == 9189933.70


def test_valor_zero_vira_nao_informado():
    lic = Licitacao.from_api({**RAW_EXEMPLO, "valorTotalEstimado": 0})
    assert lic.valor_estimado is None


def test_resumo_curto_omite_campos_vazios():
    lic = Licitacao.from_api({"numeroControlePNCP": "1-1-1/2026", "objetoCompra": "limpeza"})
    resumo = lic.resumo_curto()
    assert "valor_estimado" not in resumo
    assert resumo["objeto"] == "limpeza"
