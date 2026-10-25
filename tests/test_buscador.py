from radar.agents import buscador
from radar.pncp.models import PerfilEmpresa

PERFIL = PerfilEmpresa(
    nome="x", segmento="limpeza predial", palavras_chave=["limpeza"], uf="SP", nao_faz=["copeiragem"]
)

CANDIDATOS = [
    {"numero_controle": "1", "objeto": "Serviços de limpeza predial"},
    {"numero_controle": "2", "objeto": "Aquisição de materiais de limpeza"},
    {"numero_controle": "3", "objeto": "Copeiragem"},
]


def test_triagem_mantem_aderentes_e_descarta_sem_veredito(monkeypatch):
    def llm_falso(provedor, sistema, usuario):
        return {"itens": [
            {"id": "1", "aderente": True, "motivo": "serviço principal"},
            {"id": "2", "aderente": False, "motivo": "compra de material"},
        ]}

    monkeypatch.setattr(buscador, "chat_json", llm_falso)
    aderentes = buscador.triar(CANDIDATOS, PERFIL)
    assert [a["numero_controle"] for a in aderentes] == ["1"]
    assert aderentes[0]["motivo_triagem"] == "serviço principal"


def test_triagem_divide_em_lotes(monkeypatch):
    chamadas = []

    def llm_falso(provedor, sistema, usuario):
        chamadas.append(usuario)
        return {"itens": []}

    monkeypatch.setattr(buscador, "chat_json", llm_falso)
    muitos = [{"numero_controle": str(i), "objeto": "limpeza"} for i in range(buscador.LOTE_TRIAGEM + 1)]
    buscador.triar(muitos, PERFIL)
    assert len(chamadas) == 2
