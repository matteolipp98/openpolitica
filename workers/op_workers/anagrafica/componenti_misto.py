"""Partito dei parlamentari del gruppo misto, dalle componenti politiche (ADR 0027, issue #78).

Il gruppo misto non corrisponde a un partito: i seggi e i voti dei suoi membri si attribuiscono per persona
(core.partito_alla_data). Qui si scrivono in core.appartenenza le righe di tipo 'partito' che servono:
- Camera: componenti e membri da dati.camera.it (ocd:componenteGruppoMisto), una sola richiesta;
- Senato: dati.senato.it non pubblica le componenti, quindi vengono da content/componenti-misto.yaml.
La corrispondenza componente -> partito è sempre in content/componenti-misto.yaml.

Idempotente: una riga uguale (persona, partito, inizio) già presente non si ripete. Le persone che non sono
ancora nel database (le crea l'import dei voti) si saltano e si riprendono al giro dopo.

Uso: python -m op_workers.anagrafica.componenti_misto  (con DATABASE_URL)
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import psycopg

from op_workers.anagrafica.sincronizza import CONTENT, leggi
from op_workers.comuni.sparql import ClientSparql
from op_workers.connettori.base import DatoInatteso
from op_workers.connettori.camera import ENDPOINT, RE_DEPUTATO, data_camera, legislatura_uri

RE_COMPONENTE = re.compile(r"componenteGruppoMisto\.rdf/(cgm\d+)$")
SCHEDA_SENATORE = "https://www.senato.it/composizione/senatori/elenco-alfabetico/scheda-attivita?did={}"


@dataclass(frozen=True)
class Adesione:
    """Una persona in una componente politica che corrisponde a un partito, per un periodo."""

    ramo: str
    id_persona_esterno: str
    partito: str
    valido_dal: date
    valido_al: date | None
    fonte_url: str


@dataclass
class Esito:
    inserite: int = 0
    persone_mancanti: list[str] = field(default_factory=list)
    componenti_sconosciute: set[str] = field(default_factory=set)


def query_componenti_camera(leg: int) -> str:
    return f"""
SELECT DISTINCT ?c ?dep ?ini ?fin WHERE {{
  ?c a ocd:componenteGruppoMisto ; ocd:rif_leg {legislatura_uri(leg)} ; ocd:siComponeDi ?x .
  ?x ocd:rif_deputato ?dep ; ocd:startDate ?ini .
  OPTIONAL {{ ?x ocd:endDate ?fin }}
}} ORDER BY ?c ?dep ?ini"""


def adesioni_camera(righe: Iterable[dict[str, str]], mappa: dict[str, str | None], esito: Esito) -> list[Adesione]:
    """Dalle righe della Camera alle adesioni con partito. Le componenti senza partito si saltano; quelle che
    non sono in content/componenti-misto.yaml si segnalano (va deciso a quale partito corrispondono)."""
    out: dict[tuple[str, str, date], Adesione] = {}
    for r in righe:
        m = RE_COMPONENTE.search(r["c"])
        d = RE_DEPUTATO.search(r["dep"])
        if not m or not d:
            raise DatoInatteso(f"componente del misto Camera: URI inattese {r['c']!r} {r['dep']!r}")
        cgm = m.group(1)
        if cgm not in mappa:
            esito.componenti_sconosciute.add(cgm)
            continue
        partito = mappa[cgm]
        if partito is None:
            continue
        a = Adesione(
            "camera",
            d.group(1),
            partito,
            data_camera(r["ini"]),
            data_camera(r["fin"]) if r.get("fin") else None,
            r["c"],
        )
        out[(a.id_persona_esterno, a.partito, a.valido_dal)] = a  # il dataset ripete le righe
    return list(out.values())


def adesioni_senato(voce: dict) -> list[Adesione]:
    return [
        Adesione(
            "senato",
            str(a["senatore"]),
            a["partito"],
            a["valido_dal"],
            a.get("valido_al"),
            SCHEDA_SENATORE.format(a["senatore"]),
        )
        for a in voce.get("adesioni", [])
    ]


def salva(conn: psycopg.Connection, adesioni: Iterable[Adesione], esito: Esito) -> Esito:
    for a in adesioni:
        persona = conn.execute(
            "select persona_id from core.persona_id_esterno where fonte = %s and id_esterno = %s",
            (a.ramo, a.id_persona_esterno),
        ).fetchone()
        if not persona:
            esito.persone_mancanti.append(f"{a.ramo}:{a.id_persona_esterno}")
            continue
        partito = conn.execute("select id from core.partito where slug = %s", (a.partito,)).fetchone()
        if not partito:
            raise DatoInatteso(f"componenti-misto.yaml: partito sconosciuto {a.partito!r}")
        esito.inserite += conn.execute(
            """insert into core.appartenenza (persona_id, tipo, partito_id, valido_dal, valido_al, fonte_url)
               select %(pe)s, 'partito', %(pa)s, %(dal)s, %(al)s, %(fonte)s
               where not exists (select 1 from core.appartenenza x
                                 where x.persona_id = %(pe)s and x.tipo = 'partito' and x.partito_id = %(pa)s
                                   and x.valido_dal = %(dal)s)""",
            {"pe": persona[0], "pa": partito[0], "dal": a.valido_dal, "al": a.valido_al, "fonte": a.fonte_url},
        ).rowcount
    return esito


def sincronizza_componenti(
    conn: psycopg.Connection, sparql_camera: ClientSparql | None = None, cartella: Path = CONTENT
) -> Esito:
    conf = leggi("componenti-misto.yaml", cartella)
    esito = Esito()
    cam = conf["camera"]
    mappa = {c["id_esterno"]: c.get("partito") for c in cam["componenti"]}
    sparql = sparql_camera or ClientSparql(ENDPOINT)
    adesioni = adesioni_camera(sparql.select(query_componenti_camera(cam["legislatura"])), mappa, esito)
    adesioni += adesioni_senato(conf["senato"])
    return salva(conn, adesioni, esito)


def main() -> int:
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        esito = sincronizza_componenti(conn)
        conn.commit()
    print(f"appartenenze di partito dalle componenti del misto: {esito.inserite} righe nuove")
    if esito.persone_mancanti:
        print(f"persone non ancora nel database (al prossimo giro): {', '.join(esito.persone_mancanti)}")
    if esito.componenti_sconosciute:
        # Non si ferma l'import dei voti: si segnala, e finché non si decide restano negli "altri"
        print(
            f"::warning::componenti del misto della Camera da aggiungere a content/componenti-misto.yaml: "
            f"{sorted(esito.componenti_sconosciute)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
