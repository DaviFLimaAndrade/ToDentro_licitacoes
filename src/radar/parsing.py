from __future__ import annotations

from pathlib import Path

import pypdfium2 as pdfium
from pypdf import PdfReader, PdfWriter

MIN_CHARS_POR_PAGINA = 100


def ler_pdf(caminho: Path) -> tuple[str, int]:
    doc = pdfium.PdfDocument(caminho)
    try:
        return "\n".join(doc[i].get_textpage().get_text_range() for i in range(len(doc))), len(doc)
    finally:
        doc.close()


def extrair_texto(caminho: Path) -> str:
    return ler_pdf(caminho)[0]


def parece_escaneado(texto: str, paginas: int) -> bool:
    return len(texto.strip()) < MIN_CHARS_POR_PAGINA * max(paginas, 1)


def contar_paginas(caminho: Path) -> int:
    doc = pdfium.PdfDocument(caminho)
    try:
        return len(doc)
    finally:
        doc.close()


def recortar_paginas(caminho: Path, paginas: int) -> Path:
    leitor = PdfReader(caminho)
    if len(leitor.pages) <= paginas:
        return caminho
    destino = caminho.with_name(f"{caminho.stem}.p{paginas}.pdf")
    if not destino.exists():
        escritor = PdfWriter()
        for pagina in leitor.pages[:paginas]:
            escritor.add_page(pagina)
        with destino.open("wb") as f:
            escritor.write(f)
    return destino
