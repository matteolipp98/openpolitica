"""Database di prova: un database nuovo per sessione, con tutte le migrazioni applicate.

Richiede OP_TEST_DATABASE_URL (un server Postgres a cui ci si collega come superutente).
Senza, i test del database vengono saltati.
"""

import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest

MIGRAZIONI = Path(__file__).resolve().parents[3] / "supabase" / "migrations"


def _url_db(base: str, nome: str) -> str:
    return base.rsplit("/", 1)[0] + "/" + nome


@pytest.fixture(scope="session")
def db_url() -> Iterator[str]:
    base = os.environ.get("OP_TEST_DATABASE_URL")
    if not base:
        pytest.skip("OP_TEST_DATABASE_URL non impostata")
    nome = f"op_test_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(base, autocommit=True) as c:
        c.execute(f'create database "{nome}"')
    url = _url_db(base, nome)
    with psycopg.connect(url, autocommit=True) as c:
        for f in sorted(MIGRAZIONI.glob("*.sql")):
            c.execute(f.read_text(encoding="utf8"))
    yield url
    with psycopg.connect(base, autocommit=True) as c:
        c.execute(f'drop database "{nome}" with (force)')


@pytest.fixture
def conn(db_url: str) -> Iterator[psycopg.Connection]:
    """Connessione in una transazione annullata a fine test: i test non si sporcano a vicenda."""
    with psycopg.connect(db_url) as c:
        yield c
        c.rollback()
