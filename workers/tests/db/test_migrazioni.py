import uuid

import psycopg

from op_workers.comuni.migrazioni import CARTELLA, applica


def test_applica_tutte_e_poi_nessuna(db_url):
    base = db_url.rsplit("/", 1)[0]
    nome = f"op_mig_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(base + "/postgres", autocommit=True) as c:
        c.execute(f'create database "{nome}"')
    try:
        with psycopg.connect(f"{base}/{nome}") as conn:
            prime = applica(conn)
            assert prime == sorted(f.name for f in CARTELLA.glob("*.sql"))
            assert applica(conn) == []
            assert conn.execute("select count(*) from core.votazione_gruppo").fetchone()[0] == 0
    finally:
        with psycopg.connect(base + "/postgres", autocommit=True) as c:
            c.execute(f'drop database "{nome}" with (force)')
