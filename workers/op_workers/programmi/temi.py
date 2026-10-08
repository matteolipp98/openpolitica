"""Tema di ogni promessa (issue #75): uno dei 6 temi di content/temi.yaml, oppure "altro".

Le promesse valide (core.promessa_attuale) vanno al modello a lotti, documento per documento. I lotti sono
fissi: le promesse di un documento in ordine di paragrafo, a gruppi di DIMENSIONE. Di ogni lotto si mandano solo
le promesse che non hanno ancora un tema con questa versione del prompt: un lotto finito non si richiede, e un
giro interrotto (o il client a mano, #71) riprende dai lotti che mancano con gli stessi prompt.

Il modello risponde con il numero della promessa nel lotto e il tema. Le risposte con un numero che non c'è o un
tema sconosciuto si scartano e si contano: quelle promesse restano senza tema e si richiedono al giro dopo.
Risposta del modello, lotto e temi si salvano nella stessa transazione.

Due documenti con le stesse promesse (i programmi quasi uguali di una coalizione) fanno lo stesso prompt: il lotto
con la stessa impronta, già salvato con questo modello, si riusa senza richiamare il modello (#80). La sua risposta
dà il tema anche alle promesse dell'altro documento, legate allo stesso lotto.

Inizializzazione con Claude (client a mano), aggiornamenti con Gemini: una promessa che ha già un tema non si
richiede, qualunque modello l'abbia dato.

Uso: python -m op_workers.programmi.temi [--max-chiamate 20]   (con DATABASE_URL e GEMINI_API_KEY)
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

import psycopg
import yaml

from op_workers.catalogo.gemini import Gemini, QuotaEsaurita, Risposta
from op_workers.catalogo.manuale import RispostaMancante, client
from op_workers.programmi.promesse import sha

CONTENT = Path(__file__).resolve().parents[3] / "content"
PROMPT_ID = "promesse/tema"
PROMPT_VERSIONE = "v1"
DIMENSIONE = 100  # promesse per lotto: pochi lotti, risposta corta
ALTRO = "altro"


def temi() -> list[dict]:
    return yaml.safe_load((CONTENT / "temi.yaml").read_text(encoding="utf8"))["temi"]


def ammessi() -> list[str]:
    return [t["id"] for t in temi()] + [ALTRO]


def schema() -> dict:
    return {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {"n": {"type": "INTEGER"}, "tema": {"type": "STRING", "enum": ammessi()}},
            "required": ["n", "tema"],
            "propertyOrdering": ["n", "tema"],
        },
    }


@dataclass
class Voce:
    """Una promessa da classificare."""

    id: UUID
    misura: str
    citazione: str


def prompt(voci: list[Voce]) -> str:
    tpl = (CONTENT / "prompt" / f"{PROMPT_ID}.{PROMPT_VERSIONE}.md").read_text(encoding="utf8")
    elenco_temi = "\n".join(
        f'- "{t["id"]}": {t["nome"]}. {t["descrizione"]} Esempi: {", ".join(t["esempi"])}.' for t in temi()
    )
    elenco = "\n".join(f"[{n}] {v.misura} (dal testo: «{v.citazione}»)" for n, v in enumerate(voci, 1))
    return tpl.replace("{temi}", elenco_temi).replace("{promesse}", elenco)


@dataclass
class Esito:
    temi: dict[UUID, str] = field(default_factory=dict)
    scartate: list[object] = field(default_factory=list)


def controlla(risposta: object, voci: list[Voce]) -> Esito:
    """Tiene un tema valido per ogni numero del lotto; il resto si scarta. Un numero ripetuto vale la prima volta."""
    esito, validi = Esito(), set(ammessi())
    for o in risposta if isinstance(risposta, list) else []:
        n = o.get("n") if isinstance(o, dict) else None
        tema = o.get("tema") if isinstance(o, dict) else None
        if isinstance(n, str) and n.strip().isdigit():
            n = int(n)
        if not isinstance(n, int) or isinstance(n, bool) or not 1 <= n <= len(voci) or tema not in validi:
            esito.scartate.append(o)
            continue
        esito.temi.setdefault(voci[n - 1].id, tema)
    return esito


def lotti(voci: list[Voce], dimensione: int = DIMENSIONE) -> list[list[Voce]]:
    return [voci[i : i + dimensione] for i in range(0, len(voci), dimensione)]


# ---------- Database ----------


def promesse_per_documento(conn: psycopg.Connection) -> list[tuple[str, list[Voce], set[UUID]]]:
    """Per ogni documento: partiti, promesse valide in ordine fisso, quelle che hanno già un tema con questo prompt."""
    righe = conn.execute(
        """select p.documento_id,
                  (select string_agg(pa.slug, ', ' order by pa.slug) from core.programma pr
                   join core.partito pa on pa.id = pr.partito_id where pr.documento_id = p.documento_id),
                  p.id, p.misura, p.citazione,
                  exists (select 1 from core.promessa_tema t join core.promessa_tema_lotto l on l.id = t.lotto_id
                          where t.promessa_id = p.id and l.prompt_versione = %s)
           from core.promessa_attuale p
           order by 2, p.documento_id, p.paragrafo_da, p.paragrafo_a, p.registrato_il, p.id""",
        (f"{PROMPT_ID}.{PROMPT_VERSIONE}",),
    ).fetchall()
    out: dict[UUID, tuple[str, list[Voce], set[UUID]]] = {}
    for doc, partiti, pid, misura, citazione, fatto in righe:
        _, voci, fatti = out.setdefault(doc, (partiti or "", [], set()))
        voci.append(Voce(pid, misura, citazione))
        if fatto:
            fatti.add(pid)
    return list(out.values())


def salva_lotto(conn: psycopg.Connection, modello: str, testo_prompt: str, r: Risposta, esito: Esito) -> None:
    """Risposta del modello, lotto e temi in una sola transazione."""
    with conn.transaction():
        for m in {modello, r.modello}:
            conn.execute(
                "insert into core.modello (id, fornitore, famiglia) values (%s, %s, %s) on conflict do nothing",
                (m, r.fornitore, r.famiglia),
            )
        run_id = conn.execute(
            """insert into core.run_modello (stadio, modello_id, prompt_id, prompt_versione, input_sha256,
                   prompt_renderizzato, output, token_in, token_out, latenza_ms)
               values ('programmi.temi', %s, %s, %s, %s, %s, %s, %s, %s, %s) returning id""",
            (r.modello, PROMPT_ID, PROMPT_VERSIONE, sha(testo_prompt), testo_prompt,
             json.dumps(r.dati, ensure_ascii=False), r.token_in, r.token_out, r.latenza_ms),
        ).fetchone()[0]  # fmt: skip
        lotto_id = conn.execute(
            """insert into core.promessa_tema_lotto (modello_id, prompt_versione, input_sha256, run_modello_id,
                   classificate, scartate)
               values (%s, %s, %s, %s, %s, %s) returning id""",
            (modello, f"{PROMPT_ID}.{PROMPT_VERSIONE}", sha(testo_prompt), run_id, len(esito.temi),
             len(esito.scartate)),
        ).fetchone()[0]  # fmt: skip
        with conn.cursor() as cur:
            cur.executemany(
                "insert into core.promessa_tema (promessa_id, lotto_id, tema) values (%s, %s, %s)",
                [(pid, lotto_id, tema) for pid, tema in esito.temi.items()],
            )


def lotto_salvato(conn: psycopg.Connection, modello: str, testo_prompt: str) -> tuple[UUID, object] | None:
    """Il lotto con la stessa impronta già salvato per questo modello e prompt, con la risposta del modello."""
    return conn.execute(
        """select l.id, r.output from core.promessa_tema_lotto l join core.run_modello r on r.id = l.run_modello_id
           where l.modello_id = %s and l.prompt_versione = %s and l.input_sha256 = %s""",
        (modello, f"{PROMPT_ID}.{PROMPT_VERSIONE}", sha(testo_prompt)),
    ).fetchone()


def riusa_lotto(conn: psycopg.Connection, lotto_id: UUID, esito: Esito) -> None:
    """Temi di altre promesse con lo stesso testo, legati al lotto già salvato."""
    with conn.transaction(), conn.cursor() as cur:
        cur.executemany(
            "insert into core.promessa_tema (promessa_id, lotto_id, tema) values (%s, %s, %s) on conflict do nothing",
            [(pid, lotto_id, tema) for pid, tema in esito.temi.items()],
        )


@dataclass
class Conteggio:
    partiti: str
    lotti: int = 0
    gia_fatti: int = 0
    nuovi: int = 0
    riusati: int = 0
    classificate: int = 0
    scartate: int = 0
    mancanti: int = 0


def esegui(conn: psycopg.Connection, gemini: Gemini, dimensione: int = DIMENSIONE) -> tuple[list[Conteggio], bool]:
    """Lavora i lotti con promesse ancora senza tema. Restituisce i conteggi e se la quota si è esaurita."""
    out = []
    for partiti, voci, fatti in promesse_per_documento(conn):
        c = Conteggio(partiti)
        out.append(c)
        for lotto in lotti(voci, dimensione):
            c.lotti += 1
            da_fare = [v for v in lotto if v.id not in fatti]
            if not da_fare:
                c.gia_fatti += 1
                continue
            testo = prompt(da_fare)
            if salvato := lotto_salvato(conn, gemini.modello, testo):
                esito = controlla(salvato[1], da_fare)
                riusa_lotto(conn, salvato[0], esito)
                c.riusati += 1
                c.classificate += len(esito.temi)
                continue
            try:
                r = gemini.json(testo, schema())
            except RispostaMancante:  # client a mano (#71): il lotto aspetta la risposta, si va avanti
                c.mancanti += 1
                continue
            except QuotaEsaurita as e:
                print(f"Fermo: {e}. Si riprende alla prossima esecuzione.")
                return out, True
            esito = controlla(r.dati, da_fare)
            salva_lotto(conn, gemini.modello, testo, r, esito)
            c.nuovi += 1
            c.classificate += len(esito.temi)
            c.scartate += len(esito.scartate)
    return out, False


def per_partito(conn: psycopg.Connection) -> list[tuple[str, str, int]]:
    """Promesse valide per partito e tema (None = ancora senza tema)."""
    return conn.execute(
        """select pa.slug, t.tema, count(*)
           from core.promessa_attuale p
           join core.programma pr on pr.documento_id = p.documento_id
           join core.partito pa on pa.id = pr.partito_id
           left join core.promessa_tema_attuale t on t.promessa_id = p.id
           group by 1, 2 order by 1, 2"""
    ).fetchall()


def tabella(righe: list[tuple[str, str | None, int]]) -> str:
    """Tabella partito × tema in Markdown."""
    colonne = [*ammessi(), None]
    nomi = {**{t["id"]: t["nome"] for t in temi()}, ALTRO: "Altro", None: "Senza tema"}
    conti: dict[str, dict] = {}
    for partito, tema, n in righe:
        conti.setdefault(partito, {})[tema] = n
    usate = [c for c in colonne if c is not None or any(None in d for d in conti.values())]
    out = ["| Partito | " + " | ".join(nomi[c] for c in usate) + " | Totale |", "|---" * (len(usate) + 2) + "|"]
    for partito, d in conti.items():
        out.append(f"| {partito} | " + " | ".join(str(d.get(c, 0)) for c in usate) + f" | {sum(d.values())} |")
    return "\n".join(out)


def riepilogo(conn: psycopg.Connection, conteggi: list[Conteggio], fermo: bool, modello: str) -> str:
    righe = [
        f"Modello: `{modello}`, prompt `{PROMPT_ID}.{PROMPT_VERSIONE}`.",
        "",
        "| Partiti | Lotti | Già fatti | Fatti ora | Riusati | Senza risposta | Promesse classificate ora "
        "| Scartate ora |",
        "|---|---|---|---|---|---|---|---|",
        *[
            f"| {c.partiti} | {c.lotti} | {c.gia_fatti} | {c.nuovi} | {c.riusati} | {c.mancanti} "
            f"| {c.classificate} | {c.scartate} |"
            for c in conteggi
        ],
        "",
        "Promesse per partito e tema (un programma comune conta per ogni partito):",
        "",
        tabella(per_partito(conn)),
    ]
    if fermo:
        righe += ["", "Quota finita: restano lotti da fare."]
    return "\n".join(righe)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-chiamate", type=int, default=20)
    a = ap.parse_args()
    gemini = client(a.max_chiamate)
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
        conteggi, fermo = esegui(conn, gemini)
        print(riepilogo(conn, conteggi, fermo, gemini.modello))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
