from __future__ import annotations

import sqlite3
import unicodedata
import uuid
from datetime import datetime
from pathlib import Path

from radar.pncp.models import Licitacao

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "radar.db"

ESQUEMA = """
CREATE TABLE IF NOT EXISTS licitacoes (
    numero_controle   TEXT PRIMARY KEY,
    objeto            TEXT NOT NULL,
    objeto_norm       TEXT NOT NULL,
    modalidade        TEXT,
    valor_estimado    REAL,
    data_encerramento TEXT,
    link_sistema_origem TEXT,
    orgao             TEXT,
    municipio         TEXT,
    codigo_ibge       TEXT,
    uf                TEXT,
    sincronizado_em   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_lic_local ON licitacoes (uf, codigo_ibge, data_encerramento);
CREATE VIRTUAL TABLE IF NOT EXISTS licitacoes_fts USING fts5(
    objeto_norm, content='licitacoes', tokenize='unicode61 remove_diacritics 2'
);
CREATE TABLE IF NOT EXISTS itens_resumo (
    numero_controle TEXT PRIMARY KEY,
    n_itens         INTEGER NOT NULL,
    tipo_objeto     TEXT,
    me_epp          TEXT,
    verificado_em   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS uso (
    chave TEXT NOT NULL,
    dia   TEXT NOT NULL,
    tipo  TEXT NOT NULL,
    n     INTEGER NOT NULL,
    PRIMARY KEY (chave, dia, tipo)
);
CREATE TABLE IF NOT EXISTS syncs (
    uf          TEXT PRIMARY KEY,
    executado_em TEXT NOT NULL,
    total       INTEGER NOT NULL
);
"""

CAMPOS = [
    "numero_controle", "objeto", "modalidade", "valor_estimado", "data_encerramento",
    "link_sistema_origem", "orgao", "municipio", "codigo_ibge", "uf",
]

def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower()

def conectar(caminho: Path = DB_PATH) -> sqlite3.Connection:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(caminho)
    con.row_factory = sqlite3.Row
    con.executescript(ESQUEMA)
    return con

def novo_sync_id() -> str:
    return f"{datetime.now().isoformat(timespec='seconds')}#{uuid.uuid4().hex[:8]}"

def gravar_pagina(con: sqlite3.Connection, licitacoes: list[Licitacao], sync_id: str) -> None:
    linhas = [
        {**l.model_dump(include=set(CAMPOS)), "objeto_norm": normalizar(l.objeto),
         "sincronizado_em": sync_id}
        for l in licitacoes
    ]
    colunas = CAMPOS + ["objeto_norm", "sincronizado_em"]
    with con:
        con.executemany(
            f"INSERT OR REPLACE INTO licitacoes ({', '.join(colunas)}) "
            f"VALUES ({', '.join(':' + c for c in colunas)})",
            linhas,
        )
        _reindexar(con)

def _reindexar(con: sqlite3.Connection) -> None:
    con.execute("INSERT INTO licitacoes_fts(licitacoes_fts) VALUES ('rebuild')")

def _consulta_fts(termos: list[str]) -> str:
    limpos = [t.replace('"', " ").strip() for t in termos]
    return " OR ".join(f'"{t}" *' for t in limpos if t)

def finalizar_sync(con: sqlite3.Connection, uf: str, sync_id: str) -> int:
    with con:
        con.execute(
            "DELETE FROM licitacoes WHERE uf = ? AND sincronizado_em <> ?", (uf, sync_id)
        )
        total = con.execute("SELECT COUNT(*) FROM licitacoes WHERE uf = ?", (uf,)).fetchone()[0]
        con.execute(
            "INSERT OR REPLACE INTO syncs (uf, executado_em, total) VALUES (?, ?, ?)",
            (uf, sync_id, total),
        )
        _reindexar(con)
    return total

def salvar_sync(con: sqlite3.Connection, uf: str, licitacoes: list[Licitacao]) -> int:
    sync_id = novo_sync_id()
    gravar_pagina(con, licitacoes, sync_id)
    return finalizar_sync(con, uf, sync_id)

def _consulta_texto(texto: str) -> str:
    palavras = [p for p in texto.replace('"', " ").split() if p]
    return " ".join(f'"{p}" *' for p in palavras)

def listar(
    con: sqlite3.Connection,
    uf: str,
    pagina: int = 1,
    tamanho: int = 20,
    texto: str = "",
    codigos_ibge: list[str] | None = None,
    encerra_ate: datetime | None = None,
    so_me_epp: bool = False,
) -> tuple[list[Licitacao], int]:
    consulta = _consulta_texto(texto)
    if consulta:
        base = ("FROM licitacoes_fts f JOIN licitacoes l ON l.rowid = f.rowid "
                "WHERE licitacoes_fts MATCH ? AND ")
        params: list[object] = [consulta]
    else:
        base = "FROM licitacoes l WHERE "
        params = []
    base += "l.uf = ? AND l.data_encerramento >= ?"
    params += [uf, datetime.now().isoformat(timespec="seconds")]
    if encerra_ate:
        base += " AND l.data_encerramento <= ?"
        params.append(encerra_ate.isoformat(timespec="seconds"))
    if codigos_ibge:
        base += f" AND l.codigo_ibge IN ({', '.join('?' for _ in codigos_ibge)})"
        params.extend(codigos_ibge)
    if so_me_epp:
        base += " AND l.numero_controle IN (SELECT numero_controle FROM itens_resumo WHERE me_epp = 'exclusiva')"

    total =con.execute(f"SELECT COUNT(*) {base}", params).fetchone()[0]
    ordem = "bm25(licitacoes_fts)" if consulta else "l.data_encerramento"
    linhas = con.execute(
        f"SELECT l.* {base} ORDER BY {ordem} LIMIT ? OFFSET ?",
        [*params, tamanho, (max(pagina, 1) - 1) * tamanho],
    ).fetchall()
    return [Licitacao.model_validate({c: r[c] for c in CAMPOS}) for r in linhas], total

def gravar_resumo_itens(con: sqlite3.Connection, numero: str, resumo: dict[str, object]) -> None:
    with con:
        con.execute(
            "INSERT OR REPLACE INTO itens_resumo (numero_controle, n_itens, tipo_objeto, me_epp, verificado_em) "
            "VALUES (?, ?, ?, ?, ?)",
            (numero, resumo["n_itens"], resumo.get("tipo_objeto"), resumo.get("me_epp"),
             datetime.now().isoformat(timespec="seconds")),
        )

def resumos_itens(con: sqlite3.Connection, numeros: list[str]) -> dict[str, dict[str, object]]:
    if not numeros:
        return {}
    linhas = con.execute(
        f"SELECT * FROM itens_resumo WHERE numero_controle IN ({', '.join('?' for _ in numeros)})", numeros
    ).fetchall()
    return {r["numero_controle"]: dict(r) for r in linhas}

def sem_resumo_itens(con: sqlite3.Connection, uf: str, prioridade: list[str], limite: int) -> list[str]:
    marcadores = ", ".join("?" for _ in prioridade) or "''"
    return [r[0] for r in con.execute(
        f"SELECT l.numero_controle FROM licitacoes l LEFT JOIN itens_resumo r USING (numero_controle) "
        f"WHERE l.uf = ? AND r.numero_controle IS NULL AND l.data_encerramento >= ? "
        f"ORDER BY (l.codigo_ibge IN ({marcadores})) DESC, l.data_encerramento LIMIT ?",
        [uf, datetime.now().isoformat(timespec="seconds"), *prioridade, limite],
    )]

def contar_resumos_itens(con: sqlite3.Connection, uf: str) -> int:
    return con.execute(
        "SELECT COUNT(*) FROM licitacoes l JOIN itens_resumo r USING (numero_controle) WHERE l.uf = ?", (uf,)
    ).fetchone()[0]

def uso_do_dia(con: sqlite3.Connection, chave: str, dia: str) -> dict[str, int]:
    linhas = con.execute("SELECT tipo, n FROM uso WHERE chave = ? AND dia = ?", (chave, dia)).fetchall()
    return {r["tipo"]: r["n"] for r in linhas}


def registrar_uso(con: sqlite3.Connection, chave: str, dia: str, tipo: str) -> None:
    with con:
        con.execute(
            "INSERT INTO uso (chave, dia, tipo, n) VALUES (?, ?, ?, 1) "
            "ON CONFLICT (chave, dia, tipo) DO UPDATE SET n = n + 1",
            (chave, dia, tipo),
        )


def municipios(con: sqlite3.Connection, uf: str) -> list[dict[str, object]]:
    linhas = con.execute(
        "SELECT municipio, codigo_ibge, COUNT(*) AS total FROM licitacoes "
        "WHERE uf = ? AND municipio IS NOT NULL AND data_encerramento >= ? "
        "GROUP BY municipio, codigo_ibge ORDER BY municipio",
        (uf, datetime.now().isoformat(timespec="seconds")),
    ).fetchall()
    return [dict(r) for r in linhas]

def codigo_por_municipio(con: sqlite3.Connection, nome: str, uf: str) -> str | None:
    alvo = normalizar(nome).replace("'", "").replace("-", " ").strip()
    for municipio, codigo in con.execute(
        "SELECT DISTINCT municipio, codigo_ibge FROM licitacoes WHERE uf = ? AND municipio IS NOT NULL", (uf,)
    ):
        if normalizar(municipio).replace("'", "").replace("-", " ") == alvo:
            return codigo
    return None

def ultimo_sync(con: sqlite3.Connection, uf: str) -> sqlite3.Row | None:
    return con.execute("SELECT * FROM syncs WHERE uf = ?", (uf,)).fetchone()

def buscar(
    con: sqlite3.Connection,
    uf: str,
    termos: list[str],
    encerra_ate: datetime,
    codigo_ibge: str | list[str] | None = None,
    limite: int = 10,
) -> list[Licitacao]:
    consulta = _consulta_fts(termos)
    if consulta:
        sql = ["SELECT l.* FROM licitacoes_fts f JOIN licitacoes l ON l.rowid = f.rowid",
               "WHERE licitacoes_fts MATCH ? AND"]
        params: list[object] = [consulta]
    else:
        sql = ["SELECT l.* FROM licitacoes l WHERE"]
        params = []
    sql.append("l.uf = ? AND l.data_encerramento BETWEEN ? AND ?")
    params += [
        uf, datetime.now().isoformat(timespec="seconds"), encerra_ate.isoformat(timespec="seconds"),
    ]
    codigos = [codigo_ibge] if isinstance(codigo_ibge, str) else (codigo_ibge or [])
    if codigos:
        sql.append(f"AND l.codigo_ibge IN ({', '.join('?' for _ in codigos)})")
        params.extend(codigos)
    sql.append("ORDER BY " + ("bm25(licitacoes_fts)" if consulta else "l.data_encerramento"))
    sql.append("LIMIT ?")
    params.append(limite)
    linhas = con.execute(" ".join(sql), params).fetchall()
    return [Licitacao.model_validate({c: r[c] for c in CAMPOS}) for r in linhas]
