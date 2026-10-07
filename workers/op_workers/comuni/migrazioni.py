"""Applica le migrazioni di supabase/migrations/ non ancora applicate (registro: public.op_migrazioni).

Ogni file è una transazione: o entra tutto o niente. Rieseguito, non fa nulla.

Uso: python -m op_workers.comuni.migrazioni  (con DATABASE_URL)
"""

from __future__ import annotations

import os
from pathlib import Path

import psycopg

CARTELLA = Path(__file__).resolve().parents[3] / "supabase" / "migrations"


def applica(conn: psycopg.Connection, cartella: Path = CARTELLA) -> list[str]:
    conn.execute(
        """create table if not exists public.op_migrazioni (
             nome text primary key, applicata_il timestamptz not null default now())"""
    )
    conn.commit()
    fatte = {r[0] for r in conn.execute("select nome from public.op_migrazioni")}
    applicate = []
    for f in sorted(cartella.glob("*.sql")):
        if f.name in fatte:
            continue
        with conn.transaction():
            conn.execute(f.read_text(encoding="utf8"))
            conn.execute("insert into public.op_migrazioni (nome) values (%s)", (f.name,))
        applicate.append(f.name)
    return applicate


def main() -> int:
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        applicate = applica(conn)
    print("Migrazioni applicate:", ", ".join(applicate) if applicate else "nessuna, il database è aggiornato")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
