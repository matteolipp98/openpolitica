"""Raccoglie notizie, annunci e messaggi dalle fonti di content/fonti.yaml e li salva in core.documento_grezzo.

Per ogni fonte attiva: elenco degli elementi (feed, pagina d'elenco o sitemap, canale Telegram), solo quelli
con un indirizzo mai visto, al massimo MAX_NUOVI per passaggio. Poi:
- giornali e agenzie (livello C): si tiene l'articolo solo se titolo o sommario nominano una persona del
  perimetro; il testo scade dopo GIORNI_C giorni e non si salva se l'editore si oppone al text and data mining;
- partiti, governo e politici (livelli A e B): si tiene tutto, con il testo intero.
In più, GDELT: articoli di tutte le testate italiane che nominano le persone del perimetro.
Doppioni: stesso indirizzo o stessa impronta del testo pulito. A ogni passaggio si cancellano i testi scaduti.

Nessun modello qui: l'estrazione delle dichiarazioni è un passo successivo (#42).

Uso: python -m op_workers.notizie.raccogli [--solo ID ...]  (con DATABASE_URL)
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import psycopg
import yaml

from op_workers.notizie.connettori import (
    Elemento,
    ErroreFonte,
    da_gdelt,
    da_rss,
    da_sito,
    da_telegram,
    estrai_pagina,
    figli_sitemap,
    url_gdelt,
)
from op_workers.notizie.rete import NonPermesso, Rete, dominio
from op_workers.notizie.testo import Perimetro, impronta, pulisci, sospetto

CONTENT = Path(__file__).resolve().parents[3] / "content"
MAX_NUOVI = 30  # pagine lette per fonte e per passaggio: il primo passaggio non deve durare ore
GIORNI_C = 7  # ADR 0003: il testo dei giornali si cancella dopo una settimana


def leggi(nome: str, cartella: Path = CONTENT) -> Any:
    return yaml.safe_load((cartella / nome).read_text(encoding="utf8"))


def carica_perimetro(cartella: Path = CONTENT) -> tuple[Perimetro, list[str]]:
    """Il riconoscitore dei nomi del perimetro e l'elenco delle forme dei nomi (per la ricerca su GDELT)."""
    alias = [leggi(f"alias/{p['slug']}.yaml", cartella) for p in leggi("perimetro.yaml", cartella)["persone"]]
    cognomi = [a["cognome"] for a in alias] + [e["forma"] for a in alias for e in a.get("forme_escluse", [])]
    return Perimetro({a["slug"]: a["forme"] for a in alias}, cognomi), [f for a in alias for f in a["forme"]]


@dataclass
class Conteggio:
    fonte: str
    trovati: int = 0
    nuovi: int = 0
    fuori: int = 0
    errore: str | None = None
    avvisi: list[str] = field(default_factory=list)


@dataclass
class Fonte:
    id: str
    livello: str
    canale: str
    url: str = ""
    link: str | None = None
    sitemap: str | None = None
    filtra: bool = False  # tenere solo i documenti che nominano qualcuno del perimetro

    @classmethod
    def da_yaml(cls, f: dict) -> Fonte:
        return cls(
            f["id"], f["livello"], f["canale"], f["url"], f.get("link"), f.get("sitemap"), filtra=f["livello"] == "C"
        )


def fonti_attive(cartella: Path = CONTENT) -> tuple[list[Fonte], dict]:
    conf = leggi("fonti.yaml", cartella)
    return [Fonte.da_yaml(f) for f in conf["fonti"] if f.get("attiva", True)], conf["gdelt"]


def elenco(rete: Rete, fonte: Fonte, perimetro_forme: list[str], gdelt: dict) -> list[Elemento]:
    if fonte.canale == "gdelt":
        r = rete.scarica(url_gdelt(perimetro_forme, gdelt["filtro"], gdelt["finestra_ore"]))
        return da_gdelt(r.content)
    r = rete.scarica(fonte.url)
    if fonte.canale == "rss":
        return da_rss(r.content)
    if fonte.canale == "sito":
        if fonte.sitemap:  # indice di sitemap: si aprono quelle indicate
            pagine = [rete.scarica(u) for u in figli_sitemap(r.content, fonte.sitemap)]
            elementi = [e for p in pagine for e in da_sito(p.content, str(p.url), fonte.link or "")]
            return sorted(elementi, key=lambda e: e.pubblicato_il or datetime.min.replace(tzinfo=UTC), reverse=True)
        return da_sito(r.content, str(r.url), fonte.link or "")
    if fonte.canale == "telegram":
        return da_telegram(r.content)
    raise ValueError(f"canale sconosciuto: {fonte.canale}")


def gia_visti(conn: psycopg.Connection, urls: list[str]) -> set[str]:
    return {r[0] for r in conn.execute("select url from core.documento_grezzo where url = any(%s)", (urls,))}


def leggi_pagina(rete: Rete, el: Elemento, conteggio: Conteggio) -> tuple[str | None, bool]:
    """Testo della pagina dell'elemento e se l'editore si oppone al text and data mining."""
    try:
        r = rete.scarica(el.url)
    except NonPermesso:
        conteggio.avvisi.append(f"robots.txt non permette {el.url}")
        return None, False
    except httpx.HTTPError as e:
        conteggio.avvisi.append(f"{el.url}: {e!r}"[:200])
        return None, False
    tdm = rete.tdm_riservato(r)
    titolo, testo, data = estrai_pagina(r.content, str(r.url))
    el.titolo = el.titolo or titolo
    el.pubblicato_il = el.pubblicato_il or data
    return testo, tdm


def salva(
    conn: psycopg.Connection, fonte: Fonte, el: Elemento, testo: str | None, tdm: bool, soggetti: list[str], adesso
) -> int:
    corpo = None if tdm and fonte.livello == "C" else (testo or None)
    scade = adesso + timedelta(days=GIORNI_C) if fonte.livello == "C" and corpo else None
    return conn.execute(
        """insert into core.documento_grezzo
             (fonte, livello, canale, url, dominio, titolo, pubblicato_il, sha256, testo, testo_scade_il,
              tdm_riservato, soggetti, sospetto)
           values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
           on conflict do nothing""",
        (
            fonte.id,
            fonte.livello,
            fonte.canale,
            el.url,
            el.dominio or dominio(el.url),
            el.titolo,
            el.pubblicato_il,
            impronta(el.titolo, corpo or el.url),
            corpo,
            scade,
            tdm,
            soggetti,
            sospetto(f"{el.titolo or ''}\n{corpo or ''}"),
        ),
    ).rowcount


def raccogli_fonte(
    conn: psycopg.Connection,
    rete: Rete,
    fonte: Fonte,
    perimetro: Perimetro,
    forme: list[str],
    gdelt: dict,
    adesso: datetime,
) -> Conteggio:
    c = Conteggio(fonte.id)
    try:
        elementi = elenco(rete, fonte, forme, gdelt)
    except (httpx.HTTPError, NonPermesso, ErroreFonte) as e:
        c.errore = repr(e)[:300]
        return c
    c.trovati = len(elementi)
    visti = gia_visti(conn, [e.url for e in elementi])
    nuovi = [e for e in elementi if e.url not in visti]
    letti = 0
    for el in nuovi:
        # Giornali: primo filtro su titolo e sommario del feed, per non scaricare articoli che non ci riguardano
        if fonte.filtra and fonte.canale == "rss" and not perimetro.nomina(el.titolo, el.sommario):
            c.fuori += 1
            continue
        if letti >= MAX_NUOVI:
            break
        letti += 1
        if el.testo is not None:
            testo, tdm = el.testo, False
        else:
            testo, tdm = leggi_pagina(rete, el, c)
            if tdm and fonte.livello == "C":
                testo = None  # l'editore si oppone al text and data mining: si guarda solo il titolo
            elif testo is None:
                testo = pulisci(el.sommario) or None
        soggetti = perimetro.trova(el.titolo, testo)
        if fonte.filtra and not perimetro.nomina(el.titolo, testo):
            c.fuori += 1
            continue
        c.nuovi += salva(conn, fonte, el, testo, tdm, soggetti, adesso)
    return c


def cancella_scaduti(conn: psycopg.Connection, adesso: datetime) -> int:
    return conn.execute(
        """update core.documento_grezzo set testo = null, testo_cancellato_il = %s
           where testo is not null and testo_scade_il <= %s""",
        (adesso, adesso),
    ).rowcount


def registra(conn: psycopg.Connection, c: Conteggio) -> None:
    conn.execute(
        "insert into core.raccolta (fonte, trovati, nuovi, fuori, errore) values (%s, %s, %s, %s, %s)",
        (c.fonte, c.trovati, c.nuovi, c.fuori, c.errore),
    )


def raccogli(
    conn: psycopg.Connection, rete: Rete, cartella: Path = CONTENT, solo: set[str] | None = None
) -> tuple[list[Conteggio], int]:
    adesso = datetime.now(UTC)
    fonti, gdelt = fonti_attive(cartella)
    if gdelt["attiva"]:
        fonti.append(Fonte("gdelt", gdelt["livello"], "gdelt", filtra=True))
    perimetro, forme = carica_perimetro(cartella)
    conteggi = []
    for fonte in fonti:
        if solo and fonte.id not in solo:
            continue
        try:
            c = raccogli_fonte(conn, rete, fonte, perimetro, forme, gdelt, adesso)
        except Exception as e:  # noqa: BLE001 - una fonte rotta non deve fermare le altre
            conn.rollback()
            c = Conteggio(fonte.id, errore=repr(e)[:300])
        registra(conn, c)
        conn.commit()
        conteggi.append(c)
    cancellati = cancella_scaduti(conn, adesso)
    conn.commit()
    return conteggi, cancellati


def rapporto(conteggi: list[Conteggio], cancellati: int) -> str:
    righe = [
        "## Raccolta di notizie e dichiarazioni",
        "",
        "| Fonte | Trovati | Nuovi | Fuori perimetro | Esito |",
        "|---|---:|---:|---:|---|",
    ]
    for c in conteggi:
        esito = f"errore: {c.errore}" if c.errore else (f"{len(c.avvisi)} pagine non lette" if c.avvisi else "ok")
        righe.append(f"| {c.fonte} | {c.trovati} | {c.nuovi} | {c.fuori} | {esito} |")
    righe += ["", f"Documenti nuovi: {sum(c.nuovi for c in conteggi)}. Testi scaduti cancellati: {cancellati}."]
    avvisi = [a for c in conteggi for a in c.avvisi]
    if avvisi:
        righe += ["", "Pagine non lette (prime 20):", *[f"- {a}" for a in avvisi[:20]]]
    return "\n".join(righe)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--solo", nargs="*", help="id delle fonti da leggere (tutte se assente)")
    args = ap.parse_args(argv)
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conteggi, cancellati = raccogli(conn, Rete(), solo=set(args.solo) if args.solo else None)
    print(rapporto(conteggi, cancellati))
    # Fallisce solo se non funziona nessuna fonte: una fonte rotta si vede nel rapporto e in core.raccolta
    return 1 if conteggi and all(c.errore for c in conteggi) else 0


if __name__ == "__main__":
    raise SystemExit(main())
