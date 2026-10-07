"""Porta l'anagrafica di content/ nel database (ADR 0025, 0027; piano §3.4).

Idempotente: rieseguita sugli stessi file non inserisce nulla. Le tabelle con periodi sono
append-only: un periodo cambiato nei file diventa una nuova riga, quella vecchia resta.

Uso: python -m op_workers.anagrafica.sincronizza  (con DATABASE_URL)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg
import yaml

CONTENT = Path(__file__).resolve().parents[3] / "content"


@dataclass
class Esito:
    inseriti: dict[str, int]

    def conta(self, tabella: str, n: int) -> None:
        self.inseriti[tabella] = self.inseriti.get(tabella, 0) + n


def leggi(nome: str, cartella: Path = CONTENT) -> Any:
    return yaml.safe_load((cartella / nome).read_text(encoding="utf8"))


def _ins(conn: psycopg.Connection, sql: str, params: tuple) -> int:
    return conn.execute(sql, params).rowcount


def sincronizza(conn: psycopg.Connection, cartella: Path = CONTENT) -> Esito:
    esito = Esito({})
    partiti = leggi("partiti.yaml", cartella)
    gruppi = leggi("gruppi.yaml", cartella)
    perimetro = leggi("perimetro.yaml", cartella)

    # Partiti e ruoli (governo/opposizione) con date
    for p in partiti["partiti"]:
        esito.conta(
            "partito",
            _ins(
                conn,
                "insert into core.partito (slug, nome) values (%s, %s) on conflict (slug) do nothing",
                (p["slug"], p["nome"]),
            ),
        )
        for r in p["ruolo"]:
            if not r.get("valido_dal"):
                continue
            esito.conta(
                "partito_ruolo",
                _ins(
                    conn,
                    """insert into core.partito_ruolo (partito_id, ruolo, valido_dal, valido_al)
                   select id, %s, %s, %s from core.partito where slug = %s
                   on conflict do nothing""",
                    (r["valore"], r["valido_dal"], r.get("valido_al"), p["slug"]),
                ),
            )

    # Gruppi: solo quelli verificati sulle fonti entrano nel database
    for g in gruppi["gruppi"]:
        if g["stato"] != "verificato":
            continue
        esito.conta(
            "gruppo_parlamentare",
            _ins(
                conn,
                """insert into core.gruppo_parlamentare (ramo, legislatura, id_esterno) values (%s, %s, %s)
               on conflict do nothing""",
                (g["ramo"], g["legislatura"], g["id_esterno"]),
            ),
        )
        per = g["periodo"]
        esito.conta(
            "gruppo_periodo",
            _ins(
                conn,
                """insert into core.gruppo_periodo (gruppo_id, nome, sigla, valido_dal, valido_al)
               select id, %s, %s, %s, %s from core.gruppo_parlamentare
               where ramo = %s and legislatura = %s and id_esterno = %s
               on conflict do nothing""",
                (
                    g["nome_contiene"],
                    g.get("sigla"),
                    per["valido_dal"],
                    per.get("valido_al"),
                    g["ramo"],
                    g["legislatura"],
                    g["id_esterno"],
                ),
            ),
        )
        for slug in g["partiti"]:
            esito.conta(
                "gruppo_partito",
                _ins(
                    conn,
                    """insert into core.gruppo_partito (gruppo_id, partito_id, valido_dal, valido_al)
                   select gp.id, p.id, %s, %s from core.gruppo_parlamentare gp, core.partito p
                   where gp.ramo = %s and gp.legislatura = %s and gp.id_esterno = %s and p.slug = %s
                   on conflict do nothing""",
                    (per["valido_dal"], per.get("valido_al"), g["ramo"], g["legislatura"], g["id_esterno"], slug),
                ),
            )

    # Persone del perimetro: identità, identificativi esterni, partito di appartenenza
    for pp in perimetro["persone"]:
        a = leggi(f"alias/{pp['slug']}.yaml", cartella)
        esito.conta(
            "persona",
            _ins(
                conn,
                "insert into core.persona (slug, nome, cognome) values (%s, %s, %s) on conflict (slug) do nothing",
                (a["slug"], a["nome"], a["cognome"]),
            ),
        )
        for ide in a.get("ids_esterni", []):
            esito.conta(
                "persona_id_esterno",
                _ins(
                    conn,
                    """insert into core.persona_id_esterno (persona_id, fonte, id_esterno, valido_dal, valido_al)
                   select id, %s, %s, %s, %s from core.persona where slug = %s
                   on conflict do nothing""",
                    (ide["fonte"], ide["id"], ide["valido_dal"], ide.get("valido_al"), a["slug"]),
                ),
            )
        # Appartenenza di partito dalla carica di partito (se ha data certa), altrimenti dall'inizio legislatura
        inizio = next(
            (
                c["valido_dal"]
                for c in a["cariche"]
                if c.get("partito") == pp["partito"] and c.get("valido_dal") and not c.get("da_verificare")
            ),
            None,
        )
        esito.conta(
            "appartenenza",
            _ins(
                conn,
                """insert into core.appartenenza (persona_id, tipo, partito_id, valido_dal, fonte_url)
               select pe.id, 'partito', pa.id, %s, 'content/perimetro.yaml'
               from core.persona pe, core.partito pa where pe.slug = %s and pa.slug = %s
                 and not exists (select 1 from core.appartenenza x
                                 where x.persona_id = pe.id and x.tipo = 'partito' and x.partito_id = pa.id)""",
                (inizio or "2022-10-13", a["slug"], pp["partito"]),
            ),
        )
    return esito


def main() -> int:
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        esito = sincronizza(conn)
        conn.commit()
    for tabella, n in sorted(esito.inseriti.items()):
        print(f"{tabella}: {n} righe nuove")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
