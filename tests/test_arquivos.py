import io
import zipfile

from radar.parsing import parece_escaneado
from radar.pncp.client import _pdfs_do_zip


def _zip(arquivos: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for nome, conteudo in arquivos.items():
            zf.writestr(nome, conteudo)
    return buf.getvalue()


def test_abre_zip_dentro_de_zip():
    interno = _zip({"docs/1. Edital.pdf": b"%PDF-edital", "docs/2. Termo.pdf": b"%PDF-termo-maior"})
    externo = _zip({"RelacaoItens.pdf": b"%PDF-x", "documentos.zip": interno})
    nomes = sorted(n for n, _ in _pdfs_do_zip(externo))
    assert nomes == ["RelacaoItens.pdf", "docs/1. Edital.pdf", "docs/2. Termo.pdf"]


def test_pdf_escaneado():
    assert parece_escaneado("83 caracteres de cabeçalho", paginas=84)
    assert not parece_escaneado("texto " * 500, paginas=3)


def test_aceita_pdf_valido_mesmo_com_status_de_erro(tmp_path, monkeypatch):
    import httpx

    from radar.pncp import client as cl

    def responder(req):
        if req.url.path.endswith("/1"):
            return httpx.Response(422, content=b"%PDF-1.7 conteudo")
        return httpx.Response(422, json={"erro": "invalido"})

    monkeypatch.setattr(cl, "EDITAIS_DIR", tmp_path)
    c = cl.PNCPClient(usar_cache=False)
    c._http = httpx.Client(transport=httpx.MockTransport(responder))
    assert c.baixar_arquivo("https://x/arquivos/1", "edital").read_bytes().startswith(b"%PDF")
    try:
        c.baixar_arquivo("https://x/arquivos/2", "outro")
        assert False, "deveria falhar"
    except httpx.HTTPStatusError:
        pass


def test_repete_quando_o_pncp_devolve_422_passageiro(tmp_path, monkeypatch):
    import httpx

    from radar.pncp import client as cl

    chamadas = []

    def responder(req):
        chamadas.append(1)
        if len(chamadas) < 3:
            return httpx.Response(422, json={"message": "erro passageiro"})
        return httpx.Response(200, content=b"%PDF-1.7 ok")

    monkeypatch.setattr(cl, "EDITAIS_DIR", tmp_path)
    monkeypatch.setattr(cl.PNCPClient._baixar_com_teto.retry, "wait", lambda *_: 0)
    c = cl.PNCPClient(usar_cache=False)
    c._http = httpx.Client(transport=httpx.MockTransport(responder))
    assert c.baixar_arquivo("https://x/arquivos/1", "edital").read_bytes().startswith(b"%PDF")
    assert len(chamadas) == 3
