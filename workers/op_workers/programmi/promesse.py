"""Estrae le promesse dai programmi elettorali, una per una (ADR 0020, piano §4).

Per ogni documento di core.programma i paragrafi vanno a Gemini a lotti (ADR 0038: una sola famiglia di
modelli, poche chiamate al giorno). Il modello restituisce oggetti Promessa con uno schema JSON.
Un controllo deterministico cerca la `citazione` nel testo dei paragrafi del lotto, dopo aver normalizzato
spazi, trattini, apostrofi e virgolette: se non c'è, la promessa si scarta e si conta.

Idempotente: un lotto già lavorato con lo stesso modello e la stessa versione del prompt è registrato in
core.promessa_lotto e non si richiede di nuovo. Lotto, risposta del modello e promesse si salvano nella
stessa transazione: un'esecuzione interrotta riprende dal primo lotto non salvato.

Uso: python -m op_workers.programmi.promesse [--partito movimento-5-stelle] [--max-chiamate 20]
     (con DATABASE_URL e GEMINI_API_KEY)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

import psycopg

from op_workers.catalogo.gemini import Gemini, QuotaEsaurita, Risposta

CONTENT = Path(__file__).resolve().parents[3] / "content"
PROMPT_ID = "promesse/estrai"
PROMPT_VERSIONE = "v2"  # v2: leggere tutti i paragrafi, niente riassunti (#65)
MAX_CARATTERI = 12000  # testo per lotto: pochi lotti per programma, risposta che resta nei limiti del modello
MIN_CITAZIONE = 15  # una citazione più corta (dopo la normalizzazione) non basta a ritrovare la promessa
LIVELLI = ["nazionale", "regionale", "ue", "costituzionale"]  # più "non_chiaro", che si salva vuoto
CAMPI_FACOLTATIVI = ["beneficiari", "orizzonte", "strumento_normativo", "costo_dichiarato", "copertura_indicata"]

SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "citazione": {"type": "STRING"},
            "misura": {"type": "STRING"},
            **{c: {"type": "STRING"} for c in CAMPI_FACOLTATIVI},
            "livello_competenza": {"type": "STRING", "enum": [*LIVELLI, "non_chiaro"]},
        },
        "required": ["citazione", "misura"],
        "propertyOrdering": ["citazione", "misura", *CAMPI_FACOLTATIVI[:3], "livello_competenza",
                             *CAMPI_FACOLTATIVI[3:]],
    },
}  # fmt: skip


# ---------- Controllo della citazione ----------

_SEGNI = str.maketrans(
    {
        **dict.fromkeys("‐‑‒–—―−⁃﹘﹣－", "-"),
        **dict.fromkeys("‘’‚‛ʼʹ´`′", "'"),
        **dict.fromkeys("“”„‟«»″", '"'),
        "­": None,  # trattino morbido
    }
)


def normalizza(testo: str) -> str:
    """Forma su cui si confronta la citazione: stessi caratteri per trattini, apostrofi e virgolette,
    spazi singoli (anche attorno ai trattini e prima della punteggiatura), maiuscole ignorate."""
    t = unicodedata.normalize("NFKC", testo).translate(_SEGNI)
    t = re.sub(r"\s*-\s*", "-", t)
    t = re.sub(r"\s+([,.;:!?)\]])", r"\1", t)
    t = re.sub(r"([(\[])\s+", r"\1", t)
    return re.sub(r"\s+", " ", t).strip().casefold()


def pulisci_citazione(citazione: str) -> str:
    """Toglie spazi e virgolette che il modello mette attorno alla citazione."""
    return citazione.strip().strip("\"'«»“”‘’").strip()


def trova(citazione: str, paragrafi: list[tuple[int, str]]) -> tuple[int, int] | None:
    """I paragrafi (primo, ultimo) in cui compare la citazione, o None se non compare letteralmente.

    Si cerca nel testo del lotto unito, così una citazione che passa da un paragrafo al seguente si trova.
    """
    cit = normalizza(pulisci_citazione(citazione))
    if len(cit) < MIN_CITAZIONE:
        return None
    testi = [t for _, t in paragrafi]
    i = normalizza(" ".join(testi)).find(cit)
    if i < 0:
        return None
    # dove inizia ogni paragrafo nel testo normalizzato (a meno dello spazio che li separa)
    inizi = [len(normalizza(" ".join(testi[:k]))) for k in range(len(testi))]
    da = max(k for k, s in enumerate(inizi) if s <= i)
    a = max(k for k, s in enumerate(inizi) if s < i + len(cit))
    return paragrafi[da][0], paragrafi[a][0]


# ---------- Lotti e prompt ----------


def lotti(paragrafi: list[tuple[int, str]], max_caratteri: int = MAX_CARATTERI) -> list[list[tuple[int, str]]]:
    """Paragrafi consecutivi fino a max_caratteri di testo; un paragrafo più lungo fa lotto da solo."""
    out: list[list[tuple[int, str]]] = []
    corrente, lunghezza = [], 0
    for p in paragrafi:
        if corrente and lunghezza + len(p[1]) > max_caratteri:
            out.append(corrente)
            corrente, lunghezza = [], 0
        corrente.append(p)
        lunghezza += len(p[1])
    if corrente:
        out.append(corrente)
    return out


def prompt(lotto: list[tuple[int, str]]) -> str:
    tpl = (CONTENT / "prompt" / f"{PROMPT_ID}.{PROMPT_VERSIONE}.md").read_text(encoding="utf8")
    return tpl.replace("{paragrafi}", "\n".join(f"[{n}] {t}" for n, t in lotto))


def sha(testo: str) -> str:
    return hashlib.sha256(testo.encode()).hexdigest()


@dataclass
class Promessa:
    paragrafo_da: int
    paragrafo_a: int
    citazione: str
    misura: str
    beneficiari: str | None = None
    orizzonte: str | None = None
    strumento_normativo: str | None = None
    livello_competenza: str | None = None
    costo_dichiarato: str | None = None
    copertura_indicata: str | None = None


@dataclass
class Esito:
    promesse: list[Promessa] = field(default_factory=list)
    scartate: list[dict] = field(default_factory=list)


def controlla(risposta: object, lotto: list[tuple[int, str]]) -> Esito:
    """Tiene le promesse con citazione trovata nel testo; le altre (o malformate) sono scartate."""
    esito, viste = Esito(), set()
    for o in risposta if isinstance(risposta, list) else []:
        if not isinstance(o, dict):
            esito.scartate.append({"motivo": "non è un oggetto", "dato": o})
            continue
        citazione = pulisci_citazione(str(o.get("citazione") or ""))
        misura = str(o.get("misura") or "").strip()
        posto = trova(citazione, lotto) if misura else None
        if posto is None:
            esito.scartate.append({"motivo": "citazione non trovata" if misura else "misura vuota", **o})
            continue
        chiave = (normalizza(citazione), normalizza(misura))
        if chiave in viste:
            continue  # stessa promessa ripetuta nella stessa risposta
        viste.add(chiave)
        facoltativi = {c: (str(o.get(c) or "").strip() or None) for c in CAMPI_FACOLTATIVI}
        livello = o.get("livello_competenza")
        esito.promesse.append(
            Promessa(
                *posto, citazione, misura, **facoltativi, livello_competenza=livello if livello in LIVELLI else None
            )
        )
    return esito


# ---------- Database ----------


def documenti(conn: psycopg.Connection, partito: str | None = None) -> list[tuple[UUID, str]]:
    """Documenti dei programmi da leggere: (id, partiti). Un documento comune a più partiti compare una volta."""
    return conn.execute(
        """select d.id, string_agg(pa.slug, ', ' order by pa.slug)
           from core.documento d
           join core.programma pr on pr.documento_id = d.id
           join core.partito pa on pa.id = pr.partito_id
           where %(p)s::text is null or d.id in (
             select pr2.documento_id from core.programma pr2 join core.partito p2 on p2.id = pr2.partito_id
             where p2.slug = %(p)s)
           group by d.id order by min(pa.slug)""",
        {"p": partito},
    ).fetchall()


def paragrafi_di(conn: psycopg.Connection, documento_id: UUID) -> list[tuple[int, str]]:
    return conn.execute(
        "select n, testo from core.documento_paragrafo where documento_id = %s order by n", (documento_id,)
    ).fetchall()


def gia_fatto(conn: psycopg.Connection, documento_id: UUID, modello: str, impronta: str) -> bool:
    return (
        conn.execute(
            """select 1 from core.promessa_lotto
               where documento_id = %s and modello_id = %s and prompt_versione = %s and input_sha256 = %s""",
            (documento_id, modello, f"{PROMPT_ID}.{PROMPT_VERSIONE}", impronta),
        ).fetchone()
        is not None
    )


def salva_lotto(
    conn: psycopg.Connection, documento_id: UUID, lotto: list[tuple[int, str]], modello: str, testo_prompt: str,
    r: Risposta, esito: Esito,
) -> None:  # fmt: skip
    """Risposta del modello, lotto e promesse in una sola transazione."""
    with conn.transaction():
        for m in {modello, r.modello}:
            conn.execute(
                """insert into core.modello (id, fornitore, famiglia) values (%s, 'google', 'gemini')
                   on conflict do nothing""",
                (m,),
            )
        run_id = conn.execute(
            """insert into core.run_modello (stadio, modello_id, prompt_id, prompt_versione, input_sha256,
                   prompt_renderizzato, output, token_in, token_out, latenza_ms)
               values ('programmi.promesse', %s, %s, %s, %s, %s, %s, %s, %s, %s) returning id""",
            (r.modello, PROMPT_ID, PROMPT_VERSIONE, sha(testo_prompt), testo_prompt,
             json.dumps(r.dati, ensure_ascii=False), r.token_in, r.token_out, r.latenza_ms),
        ).fetchone()[0]  # fmt: skip
        lotto_id = conn.execute(
            """insert into core.promessa_lotto (documento_id, paragrafo_da, paragrafo_a, modello_id, prompt_versione,
                   input_sha256, run_modello_id, estratte, scartate)
               values (%s, %s, %s, %s, %s, %s, %s, %s, %s) returning id""",
            (documento_id, lotto[0][0], lotto[-1][0], modello, f"{PROMPT_ID}.{PROMPT_VERSIONE}", sha(testo_prompt),
             run_id, len(esito.promesse), len(esito.scartate)),
        ).fetchone()[0]  # fmt: skip
        for p in esito.promesse:
            conn.execute(
                """insert into core.promessa (documento_id, lotto_id, paragrafo_da, paragrafo_a, citazione, misura,
                       beneficiari, orizzonte, strumento_normativo, livello_competenza, costo_dichiarato,
                       copertura_indicata)
                   values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (documento_id, lotto_id, p.paragrafo_da, p.paragrafo_a, p.citazione, p.misura, p.beneficiari,
                 p.orizzonte, p.strumento_normativo, p.livello_competenza, p.costo_dichiarato,
                 p.copertura_indicata),
            )  # fmt: skip


@dataclass
class Conteggio:
    partiti: str
    lotti: int = 0
    gia_fatti: int = 0
    nuovi: int = 0
    estratte: int = 0
    scartate: int = 0
    esempi_scartati: list[dict] = field(default_factory=list)


def esegui(
    conn: psycopg.Connection, gemini: Gemini, partito: str | None = None, max_caratteri: int = MAX_CARATTERI
) -> tuple[list[Conteggio], bool]:
    """Lavora i lotti non ancora fatti. Restituisce i conteggi per documento e se la quota si è esaurita."""
    out = []
    for documento_id, partiti in documenti(conn, partito):
        c = Conteggio(partiti)
        out.append(c)
        for lotto in lotti(paragrafi_di(conn, documento_id), max_caratteri):
            c.lotti += 1
            testo = prompt(lotto)
            if gia_fatto(conn, documento_id, gemini.modello, sha(testo)):
                c.gia_fatti += 1
                continue
            try:
                r = gemini.json(testo, SCHEMA)
            except QuotaEsaurita as e:
                print(f"Fermo: {e}. Si riprende alla prossima esecuzione.")
                return out, True
            esito = controlla(r.dati, lotto)
            salva_lotto(conn, documento_id, lotto, gemini.modello, testo, r, esito)
            c.nuovi += 1
            c.estratte += len(esito.promesse)
            c.scartate += len(esito.scartate)
            c.esempi_scartati += esito.scartate[: max(0, 3 - len(c.esempi_scartati))]
    return out, False


def riepilogo(conn: psycopg.Connection, conteggi: list[Conteggio], fermo: bool, modello: str) -> str:
    righe = [
        f"Modello: `{modello}`, prompt `{PROMPT_ID}.{PROMPT_VERSIONE}`.",
        "",
        "| Partiti | Lotti | Già fatti | Fatti ora | Promesse tenute ora | Scartate ora |",
        "|---|---|---|---|---|---|",
        *[f"| {c.partiti} | {c.lotti} | {c.gia_fatti} | {c.nuovi} | {c.estratte} | {c.scartate} |" for c in conteggi],
        "",
    ]
    tot = conn.execute("select count(*) from core.promessa").fetchone()[0]
    righe.append(f"Promesse nel database: {tot}." + (" Quota finita: restano lotti da fare." if fermo else ""))
    esempi = [e for c in conteggi for e in c.esempi_scartati]
    if esempi:
        righe += ["", "Esempi di scarti (citazione non trovata nel testo):", ""]
        righe += [f"- {e.get('motivo')}: «{str(e.get('citazione', ''))[:200]}»" for e in esempi[:5]]
    return "\n".join(righe)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--partito", help="slug di un partito: solo il suo programma")
    ap.add_argument("--max-chiamate", type=int, default=20)
    a = ap.parse_args()
    gemini = Gemini(max_chiamate=a.max_chiamate)
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
        conteggi, fermo = esegui(conn, gemini, a.partito)
        print(riepilogo(conn, conteggi, fermo, gemini.modello))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
