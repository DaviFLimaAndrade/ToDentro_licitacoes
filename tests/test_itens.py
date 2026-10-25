from radar.itens import fracao_valor, resumir

EXCLUSIVA = "Participação exclusiva para ME/EPP"
SEM = "Sem benefício"


def _item(tipo: str, beneficio: str, valor: float = 100.0, descricao: str = "x") -> dict:
    return {"materialOuServico": tipo, "tipoBeneficioNome": beneficio, "valorTotal": valor, "descricao": descricao}


def test_servico_exclusivo_me_epp():
    r = resumir([_item("S", EXCLUSIVA), _item("S", EXCLUSIVA)])
    assert (r.tipo_objeto, r.me_epp, r.n_itens) == ("servico", "exclusiva", 2)


def test_misto_com_beneficio_em_parte_dos_itens():
    r = resumir([_item("M", EXCLUSIVA), _item("S", SEM)])
    assert (r.tipo_objeto, r.me_epp) == ("misto", "parcial")


def test_sem_itens():
    assert resumir([]).tipo_objeto is None


def test_fracao_valor():
    itens = [_item("S", SEM, 300, "limpeza"), _item("S", SEM, 100, "copa")]
    assert fracao_valor(itens, lambda i: "limpeza" in i["descricao"]) == 0.75
