from datetime import datetime, timedelta

from radar import db
from radar.pncp.models import Licitacao


def _lic(numero: str, objeto: str, ibge: str = "3509502", dias: int = 5) -> Licitacao:
    encerra = (datetime.now() + timedelta(days=dias)).isoformat(timespec="seconds")
    return Licitacao(
        numero_controle=numero, objeto=objeto, uf="SP", codigo_ibge=ibge,
        municipio="Campinas", data_encerramento=encerra,
    )


def test_buscar_filtra_termo_sem_acento_municipio_e_prazo(tmp_path):
    con = db.conectar(tmp_path / "t.db")
    db.salvar_sync(con, "SP", [
        _lic("1", "Serviços de LIMPEZA e conservação predial"),
        _lic("2", "Aquisição de papel A4"),
        _lic("3", "Limpeza de vias", ibge="3550308"),
        _lic("4", "Limpeza hospitalar", dias=120),
        _lic("5", "Limpeza encerrada", dias=-1),
    ])
    achadas = db.buscar(con, "SP", ["conservacao", "limpeza"],
                        encerra_ate=datetime.now() + timedelta(days=30), codigo_ibge="3509502")
    assert [l.numero_controle for l in achadas] == ["1"]


def test_fts_pega_plural_e_ordena_por_relevancia(tmp_path):
    con = db.conectar(tmp_path / "t.db")
    db.salvar_sync(con, "SP", [
        _lic("1", "Aquisição de materiais diversos, incluindo produtos de limpeza"),
        _lic("2", "Serviços de limpeza, limpeza hospitalar e limpezas de vidros"),
        _lic("3", "Serviços de jardinagem"),
    ])
    achadas = db.buscar(con, "SP", ["limpeza"], encerra_ate=datetime.now() + timedelta(days=30))
    assert [l.numero_controle for l in achadas] == ["2", "1"]


def test_listar_pagina_conta_e_exige_todas_as_palavras(tmp_path):
    con = db.conectar(tmp_path / "t.db")
    db.salvar_sync(con, "SP", [
        _lic(str(i), "Limpeza hospitalar" if i % 2 else "Limpeza predial", dias=i + 1) for i in range(25)
    ] + [_lic("velha", "Limpeza hospitalar", dias=-2)])
    itens, total = db.listar(con, "SP", pagina=2, tamanho=10)
    assert total == 25 and len(itens) == 10
    assert itens[0].numero_controle == "10"
    _, total = db.listar(con, "SP", texto="limpeza hospitalar")
    assert total == 12


def test_termo_com_aspas_nao_quebra_a_consulta(tmp_path):
    con = db.conectar(tmp_path / "t.db")
    db.salvar_sync(con, "SP", [_lic("1", "limpeza predial")])
    achadas = db.buscar(con, "SP", ['limpeza "predial'], encerra_ate=datetime.now() + timedelta(days=30))
    assert [l.numero_controle for l in achadas] == ["1"]


def test_sync_substitui_retrato_anterior(tmp_path):
    con = db.conectar(tmp_path / "t.db")
    db.salvar_sync(con, "SP", [_lic("1", "limpeza"), _lic("2", "limpeza")])
    db.salvar_sync(con, "SP", [_lic("2", "limpeza")])
    assert db.ultimo_sync(con, "SP")["total"] == 1
    assert len(db.buscar(con, "SP", [], encerra_ate=datetime.now() + timedelta(days=30))) == 1
