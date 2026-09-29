"""
Acesso ao banco SQLite com configuracao segura e transacoes explicitas.

* foreign_keys=ON em TODA conexao (no SQLite elas vem desligadas por padrao);
* journal WAL: a API grava enquanto o dashboard le, sem bloqueio mutuo;
* busy_timeout: em vez de falhar na hora, espera ate 10 s por um lock;
* transacao(): BEGIN IMMEDIATE -> COMMIT, ou ROLLBACK em qualquer erro. Uma
  leitura so existe no banco junto com sua predicao, seus alertas e seus
  eventos de auditoria - nunca pela metade (atomicidade).
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .. import config


def conectar(db_path: Path | str | None = None, somente_leitura: bool = False) -> sqlite3.Connection:
    """Abre uma conexao configurada (autocommit; transacoes via `transacao`)."""
    caminho = Path(db_path or config.DB_PATH)
    if somente_leitura:
        conn = sqlite3.connect(f"file:{caminho}?mode=ro", uri=True, timeout=10,
                               check_same_thread=False, isolation_level=None)
    else:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(caminho, timeout=10, check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    if not somente_leitura:
        conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def sessao(db_path: Path | str | None = None, somente_leitura: bool = False) -> Iterator[sqlite3.Connection]:
    """Context manager que garante o fechamento da conexao."""
    conn = conectar(db_path, somente_leitura)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transacao(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Transacao atomica: tudo ou nada."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def criar_schema(conn: sqlite3.Connection) -> None:
    """Cria tabelas, triggers, visoes e indices (idempotente)."""
    conn.executescript(config.SCHEMA_PATH.read_text(encoding="utf-8"))


def banco_existe(db_path: Path | str | None = None) -> bool:
    return Path(db_path or config.DB_PATH).exists()
