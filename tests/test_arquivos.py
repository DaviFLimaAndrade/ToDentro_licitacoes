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
