from radar import db, limites


def test_conta_por_tipo_e_esgota_no_limite(tmp_path, monkeypatch):
    caminho = tmp_path / "t.db"
    monkeypatch.setattr(db, "DB_PATH", caminho)
    monkeypatch.setattr(db.conectar, "__defaults__", (caminho,))
    monkeypatch.setenv("LIMITE_RESUMOS_DIA", "2")
    chave = limites.chave_do_ip("10.0.0.1")
    assert not limites.esgotado(chave, "resumo")
    limites.consumir(chave, "resumo")
    limites.consumir(chave, "resumo")
    limites.consumir(chave, "busca")
    s = limites.situacao(chave)
    assert s["resumo"] == {"usados": 2, "limite": 2}
    assert s["busca"]["usados"] == 1
    assert limites.esgotado(chave, "resumo")
    assert not limites.esgotado(limites.chave_do_ip("10.0.0.2"), "resumo")
