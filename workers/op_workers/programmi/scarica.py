"""Scarica i programmi elettorali di content/programmi.yaml e ne salva il testo diviso in paragrafi (ADR 0020).

Per ogni programma: indirizzo ricavato dall'elenco pubblico del Ministero dell'Interno, impronta sha256,
testo pagina per pagina. Le pagine senza testo (scansioni) e quelle con un testo illeggibile (scansioni lette
male da chi ha fatto il PDF) si leggono con l'OCR (tesseract, italiano), e i loro paragrafi restano segnati.
Idempotente: un documento con la stessa impronta non si rilegge, se è già stato letto con la versione attuale
dell'estrazione (ESTRAZIONE). Letto con una versione più vecchia, si rilegge: la nuova lettura è una riga nuova
di core.documento (append-only, #63) e quella valida è la più recente (vista core.documento_attuale).

parole_it.txt.gz: le 200.000 parole italiane più frequenti secondo wordfreq 3.1.1 (Robyn Speer, dati
CC BY-SA 4.0), in minuscolo e senza accenti, solo quelle di almeno 3 lettere. Rigenerarla:
  top_n_list("it", 200000) da wordfreq, poi le stesse trasformazioni di _normale e il filtro sulle 3 lettere.

Uso: python -m op_workers.programmi.scarica  (con DATABASE_URL; tesseract serve solo per le scansioni)
"""

from __future__ import annotations

import gzip
import hashlib
import io
import os
import re
import shutil
import subprocess  # noqa: S404 - solo tesseract, con argomenti fissi
import unicodedata
from dataclasses import dataclass
from datetime import date
from functools import cache
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin

import httpx
import psycopg
import yaml

CONTENT = Path(__file__).resolve().parents[3] / "content"
FONTE = "interno-trasparenza"
TIPO_PROGRAMMA = 2  # "Programma elettorale del partito o gruppo politico" nell'elenco del Ministero
MINIMO_TESTO = 30  # sotto questi caratteri una pagina è una scansione: si legge con l'OCR
FINESTRA = 20  # parole di fila su cui si misura se il testo è leggibile
MINIMO_NOTE = 0.8  # quota minima di parole conosciute in ogni finestra: sotto, la pagina si rilegge con l'OCR
PAROLE = Path(__file__).with_name("parole_it.txt.gz")
# Versione dell'estrazione del testo: si aumenta quando cambia quello che si salva dallo stesso PDF.
# 1 = pdfplumber, OCR solo sulle pagine senza testo; 2 = OCR anche sulle pagine illeggibili (#62).
ESTRAZIONE = 2
UA = "openpolitica/0.1 (+https://github.com/matteolipp98/openpolitica)"


class ProgrammaNonTrovato(RuntimeError):
    pass


@dataclass
class Pagina:
    numero: int
    testo: str
    ocr: bool


def url_programma(elenco: dict[str, Any], url_elenco: str, contrassegno: int) -> str:
    """L'indirizzo del programma, costruito come fa il portale (dima-contrassegni.js):
    <cartella dell'elenco>/Documenti/<contrassegno><fascicolo>/<file>.

    Un contrassegno può avere più righe (una per fascicolo) con lo stesso programma: si usa la prima.
    """
    trovati = [
        (c, f)
        for c in elenco["contrass"]
        if c["n_ord"] == contrassegno
        for f in c.get("e_file") or []
        if f["tp_doc"] == TIPO_PROGRAMMA
    ]
    nomi = {f["f_doc"] for _, f in trovati}
    if len(nomi) != 1:
        raise ProgrammaNonTrovato(f"contrassegno {contrassegno}: {len(nomi)} programmi diversi nell'elenco, atteso 1")
    c, f = trovati[0]
    cartella = urljoin(url_elenco, "Documenti/")
    return f"{cartella}{contrassegno}{c.get('l_fasc') or ''}/{quote(f['f_doc'])}"


def testo_ocr(pdf: bytes, indice: int) -> str:
    """Legge una pagina scansionata: immagine a 300 dpi e tesseract in italiano."""
    import pypdfium2 as pdfium

    tesseract = shutil.which("tesseract")
    if not tesseract:
        raise RuntimeError("serve tesseract (con la lingua italiana) per leggere le pagine scansionate")
    immagine = pdfium.PdfDocument(pdf)[indice].render(scale=300 / 72).to_pil()
    png = io.BytesIO()
    immagine.save(png, format="PNG")
    esito = subprocess.run(  # noqa: S603
        [tesseract, "stdin", "stdout", "-l", "ita", "--psm", "3"],
        input=png.getvalue(),
        capture_output=True,
        check=True,
    )
    return esito.stdout.decode("utf8")


def _normale(parola: str) -> str:
    """Minuscolo e senza accenti: le scansioni lette male perdono spesso gli accenti ("piu", "priorita")."""
    scomposta = unicodedata.normalize("NFD", parola.lower())
    return "".join(c for c in scomposta if not unicodedata.combining(c))


@cache
def _dizionario() -> frozenset[str]:
    return frozenset(gzip.decompress(PAROLE.read_bytes()).decode("utf8").split())


def leggibile(testo: str) -> bool:
    """Se il testo di una pagina è italiano leggibile, e non una scansione letta male ("iientia tia le aiee").

    Si guardano le parole di almeno 3 lettere: in ogni gruppo di FINESTRA parole di fila, almeno MINIMO_NOTE
    devono essere nel dizionario. Si guarda il gruppo peggiore e non la media, perché spesso solo un pezzo
    della pagina è sbagliato. Un testo più corto della finestra si misura tutto insieme.
    """
    diz = _dizionario()
    note = [_normale(p) in diz for p in re.findall(r"[^\W\d_]+", testo) if len(p) >= 3]
    if len(note) < FINESTRA:
        return sum(note) >= MINIMO_NOTE * len(note)
    somma = peggiore = sum(note[:FINESTRA])
    for i in range(FINESTRA, len(note)):
        somma += note[i] - note[i - FINESTRA]
        peggiore = min(peggiore, somma)
    return peggiore >= MINIMO_NOTE * FINESTRA


def pagine(pdf: bytes, ocr=testo_ocr) -> list[Pagina]:
    import pdfplumber

    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        testi = [p.extract_text() or "" for p in doc.pages]
    out = []
    for i, t in enumerate(testi):
        if len(t.strip()) >= MINIMO_TESTO and leggibile(t):
            out.append(Pagina(i + 1, t, False))
        else:
            out.append(Pagina(i + 1, ocr(pdf, i), True))
    return out


PUNTO_ELENCO = re.compile(r"^\s*(?:[•●▪■◦\-–—*o]\s+|\d{1,2}[.)]\s+|[a-z][.)]\s+)")
FINE_FRASE = re.compile(r"[.!?:;]\s*$")


def paragrafi(testo: str) -> list[str]:
    """Divide il testo di una pagina in paragrafi.

    Nei PDF ogni riga va a capo: si uniscono le righe e si spezza dove c'è una riga vuota o un punto
    di elenco, dove una riga corta finisce con la fine di una frase, e dopo un titolo (riga corta senza
    punteggiatura seguita da una maiuscola). Le parole spezzate con il trattino a fine riga si ricompongono.
    """
    righe = [r.rstrip() for r in testo.splitlines()]
    piene = [len(r) for r in righe if r.strip()]
    larga = sorted(piene)[len(piene) * 3 // 4] if piene else 0  # larghezza tipica di una riga piena
    out: list[str] = []
    corrente = ""
    chiudi = titolo = False
    for r in righe:
        if not r.strip():
            chiudi = True
            continue
        inizio = r.strip()[:1]
        if corrente and (chiudi or PUNTO_ELENCO.match(r) or (titolo and inizio.isupper())):
            out.append(corrente)
            corrente = ""
        if not corrente:
            corrente = r.strip()
        elif corrente.endswith("-") and not corrente.endswith(" -") and inizio.islower():
            corrente = corrente[:-1] + r.strip()
        else:
            corrente += " " + r.strip()
        corta = len(r) < 0.85 * larga
        chiudi = corta and bool(FINE_FRASE.search(r))
        titolo = len(r) < 0.7 * larga and not re.search(r"[,.;:!?\-]\s*$", r)
    if corrente:
        out.append(corrente)
    return [re.sub(r"\s+", " ", p).strip() for p in out if len(p.strip()) > 1]


def paragrafi_documento(lette: list[Pagina]) -> list[tuple[int, str, bool]]:
    """I paragrafi di tutto il documento: (pagina dove inizia, testo, letto con l'OCR).

    Un paragrafo che continua nella pagina dopo (finisce senza punto, il seguito inizia minuscolo) si riunisce.
    """
    out: list[tuple[int, str, bool]] = []
    for p in lette:
        for i, t in enumerate(paragrafi(p.testo)):
            if i == 0 and out and t[:1].islower() and not FINE_FRASE.search(out[-1][1]):
                pagina, prima, ocr = out[-1]
                out[-1] = (pagina, f"{prima} {t}", ocr or p.ocr)
            else:
                out.append((p.numero, t, p.ocr))
    return out


def salva_documento(
    conn: psycopg.Connection, *, url: str, data: date, sha256: str, lette: list[Pagina], estrazione: int = ESTRAZIONE
) -> int:
    """Salva una lettura del documento e i suoi paragrafi. Restituisce il numero di paragrafi."""
    doc_id = conn.execute(
        """insert into core.documento (fonte, livello, url, data, sha256, pagine, pagine_ocr, estrazione)
           values (%s, 'A', %s, %s, %s, %s, %s, %s) returning id""",
        (FONTE, url, data, sha256, len(lette), sum(p.ocr for p in lette), estrazione),
    ).fetchone()[0]
    par = paragrafi_documento(lette)
    for n, (pagina, testo, ocr) in enumerate(par, start=1):
        conn.execute(
            "insert into core.documento_paragrafo (documento_id, n, pagina, testo, ocr) values (%s,%s,%s,%s,%s)",
            (doc_id, n, pagina, testo, ocr),
        )
    return len(par)


def collega(conn: psycopg.Connection, *, partiti: list[str], elezione: date, sha256: str) -> int:
    """Collega la lettura valida del documento ai partiti come loro programma. Restituisce i collegamenti nuovi.

    Dopo una rilettura il partito ha un collegamento per ogni lettura: vale quello alla lettura più recente.
    """
    nuovi = 0
    for slug in partiti:
        nuovi += conn.execute(
            """insert into core.programma (partito_id, elezione, documento_id)
               select p.id, %s, d.id from core.partito p, core.documento_attuale d where p.slug = %s and d.sha256 = %s
               on conflict do nothing""",
            (elezione, slug, sha256),
        ).rowcount
    return nuovi


def esegui(conn: psycopg.Connection, http: httpx.Client, cartella: Path = CONTENT) -> list[str]:
    conf = yaml.safe_load((cartella / "programmi.yaml").read_text(encoding="utf8"))
    righe = []
    for el in conf["elezioni"]:
        elezione = el["data"] if isinstance(el["data"], date) else date.fromisoformat(el["data"])
        r = http.get(el["elenco"])
        r.raise_for_status()
        elenco = r.json()
        for prog in el["programmi"]:
            url = url_programma(elenco, el["elenco"], prog["contrassegno"])
            pdf = http.get(url)
            pdf.raise_for_status()
            if not pdf.content.startswith(b"%PDF"):
                raise ProgrammaNonTrovato(f"{url}: non è un PDF")
            sha = hashlib.sha256(pdf.content).hexdigest()
            letto = conn.execute(
                "select estrazione, pagine, pagine_ocr from core.documento_attuale where sha256 = %s", (sha,)
            ).fetchone()
            noto = letto is not None and letto[0] >= ESTRAZIONE  # l'OCR è lento: non si rilegge senza motivo
            lette = [] if noto else pagine(pdf.content)
            with conn.transaction():
                par = 0 if noto else salva_documento(conn, url=url, data=elezione, sha256=sha, lette=lette)
                collega(conn, partiti=prog["partiti"], elezione=elezione, sha256=sha)
            pag, ocr = letto[1:] if noto else (len(lette), sum(p.ocr for p in lette))
            stato = "già letto" if noto else f"riletto ({letto[0]} → {ESTRAZIONE})" if letto else "nuovo"
            righe.append(f"| {', '.join(prog['partiti'])} | {elezione} | {pag} | {ocr} | {par} | {stato} |")
    return righe


def main() -> int:
    url_db = os.environ["DATABASE_URL"]
    with (
        psycopg.connect(url_db, autocommit=True) as conn,  # ogni programma si salva appena letto
        httpx.Client(timeout=300, headers={"User-Agent": UA}, follow_redirects=True) as http,
    ):
        righe = esegui(conn, http)
    print("| Partiti | Elezione | Pagine | Pagine con OCR | Paragrafi nuovi | Stato |")
    print("|---|---|---|---|---|---|")
    print("\n".join(righe))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
