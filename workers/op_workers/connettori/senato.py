"""Connettore Senato della Repubblica: SPARQL su dati.senato.it (struttura in docs/fonti-open-data.md).

Il server rifiuta VALUES: i filtri su più risorse usano FILTER(... IN (...)).
Il voto di ogni senatore è un arco della votazione (osr:favorevole, osr:contrario, ...).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import date

from op_workers.comuni.sparql import ClientSparql
from op_workers.connettori.base import (
    AdesioneGrezza,
    DatoInatteso,
    Espressione,
    ParlamentareGrezzo,
    VotazioneGrezza,
    VotoGrezzo,
    finestre_mensili,
)

ENDPOINT = "https://dati.senato.it/sparql"
OSR = "http://dati.senato.it/osr/"
SENATO_VOTAZIONE = "http://dati.senato.it/votazione/"

RE_VOTAZIONE = re.compile(r"/votazione/(\d+-\d+-\d+)$")
RE_SENATORE = re.compile(r"/senatore/(\d+)$")
RE_GRUPPO = re.compile(r"/gruppo/(\d+)$")

# Da un arco della votazione all'espressione; a parità di senatore vince quella con priorità più alta.
ARCHI: dict[str, tuple[Espressione, int]] = {
    "favorevole": ("favorevole", 5),
    "contrario": ("contrario", 5),
    "astenuto": ("astenuto", 5),
    "presidente": ("presidente", 4),
    "presenteNonVotante": ("non_votante", 3),
    "inCongedoMissione": ("in_missione", 2),
}


def _id(regex: re.Pattern[str], uri: str, cosa: str) -> str:
    m = regex.search(uri)
    if not m:
        raise DatoInatteso(f"{cosa}: URI inattesa {uri!r}")
    return m.group(1)


def data_iso(s: str) -> date:
    try:
        return date.fromisoformat(s[:10])
    except ValueError as e:
        raise DatoInatteso(f"data Senato non valida: {s!r}") from e


def approvata(esito: str | None) -> bool | None:
    e = (esito or "").lower()
    if "approv" in e:
        return True
    if "respint" in e or "non approv" in e:
        return False
    return None


def normalizza_votazione(riga: dict[str, str], leg: int) -> VotazioneGrezza:
    etichetta = (riga.get("label") or "").strip() or None
    e = (etichetta or "").lower()
    fase = (riga.get("fase") or "").strip()
    return VotazioneGrezza(
        ramo="senato",
        legislatura=leg,
        id_esterno=_id(RE_VOTAZIONE, riga["v"], "votazione"),
        data=data_iso(riga["data"]),
        tipo=etichetta,
        titolo=etichetta,
        descrizione=(riga.get("esito") or "").strip() or None,
        atto_ref=fase or None,  # es. 'S.1056'
        atto_titolo=(riga.get("titolo") or "").strip() or None,
        finale=e.startswith("votazione finale"),
        fiducia="fiducia" in e,
        segreta="segret" in (riga.get("tipoVot") or "").lower(),
        favorevoli=int(riga["fav"]),
        contrari=int(riga["con"]),
        astenuti=int(riga.get("ast") or 0),
        approvata=approvata(riga.get("esito")),
        url=riga["v"],
    )


def voti_da_archi(righe: list[dict[str, str]]) -> list[VotoGrezzo]:
    """Una riga per (votazione, arco, senatore) → un voto per (votazione, senatore)."""
    scelto: dict[tuple[str, str], tuple[Espressione, int]] = {}
    for r in righe:
        arco = r["p"].removeprefix(OSR)
        if arco not in ARCHI:
            raise DatoInatteso(f"arco di voto Senato sconosciuto: {r['p']!r}")
        espr, prio = ARCHI[arco]
        k = (_id(RE_VOTAZIONE, r["v"], "votazione"), _id(RE_SENATORE, r["sen"], "senatore"))
        attuale = scelto.get(k)
        if attuale and attuale[1] == prio and attuale[0] != espr:
            raise DatoInatteso(f"voti contraddittori per {k}: {attuale[0]} e {espr}")
        if not attuale or prio > attuale[1]:
            scelto[k] = (espr, prio)
    return [VotoGrezzo(v, s, e, None) for (v, s), (e, _) in sorted(scelto.items())]


def query_votazioni(leg: int, dal: date, al: date) -> str:
    return f"""
SELECT DISTINCT ?v ?data ?label ?fav ?con ?ast ?esito ?tipoVot ?titolo ?fase WHERE {{
  ?v a osr:Votazione ; osr:legislatura {leg} ; osr:seduta ?s ; osr:favorevoli ?fav ; osr:contrari ?con .
  ?s osr:dataSeduta ?data .
  OPTIONAL {{ ?v osr:astenuti ?ast }} OPTIONAL {{ ?v rdfs:label ?label }} OPTIONAL {{ ?v osr:esito ?esito }}
  OPTIONAL {{ ?v osr:tipoVotazione ?tipoVot }}
  OPTIONAL {{ ?v osr:oggetto ?o . ?o osr:relativoA ?ddl .
             OPTIONAL {{ ?ddl osr:titolo ?titolo }} OPTIONAL {{ ?ddl osr:fase ?fase }} }}
  FILTER(STR(?data) >= "{dal.isoformat()}" && STR(?data) <= "{al.isoformat()}")
}} ORDER BY ?data ?v"""


def query_votazioni_del_giorno(giorno: date) -> str:
    return f"""
SELECT DISTINCT ?v WHERE {{
  ?v a osr:Votazione ; osr:seduta ?s . ?s osr:dataSeduta ?data .
  FILTER(STR(?data) = "{giorno.isoformat()}")
}} ORDER BY ?v"""


def query_archi_votazione(uri: str) -> str:
    """I voti di una sola votazione: la query su un giorno intero è troppo pesante (HTTP 502).

    Il server rifiuta anche BIND (HTTP 400): la votazione va scritta direttamente come soggetto.
    """
    archi = ", ".join(f"osr:{a}" for a in ARCHI)
    return f"""
SELECT DISTINCT ?p ?sen WHERE {{
  <{uri}> ?p ?sen . FILTER(?p IN ({archi}))
}} ORDER BY ?sen ?p"""


def query_parlamentari(leg: int) -> str:
    return f"""
SELECT DISTINCT ?s ?nome ?cognome WHERE {{
  ?s a osr:Senatore ; foaf:firstName ?nome ; foaf:lastName ?cognome ; ?r ?m .
  ?m a ocd:mandatoSenato ; osr:legislatura {leg} .
}} ORDER BY ?s"""


def query_adesioni(leg: int) -> str:
    return f"""
SELECT DISTINCT ?s ?g ?inizio ?fine WHERE {{
  ?s ocd:aderisce ?a . ?a osr:legislatura {leg} ; osr:gruppo ?g ; osr:inizio ?inizio .
  OPTIONAL {{ ?a osr:fine ?fine }}
}} ORDER BY ?s ?inizio"""


class ConnettoreSenato:
    ramo = "senato"

    def __init__(self, sparql: ClientSparql | None = None) -> None:
        self.sparql = sparql or ClientSparql(ENDPOINT)

    def votazioni(self, legislatura: int, dal: date) -> Iterator[VotazioneGrezza]:
        visti: set[str] = set()
        righe = [
            r
            for inizio, fine in finestre_mensili(dal)
            for r in self.sparql.pagine(query_votazioni(legislatura, inizio, fine), pagina=1000)
        ]
        for r in righe:
            if r["v"] not in visti:
                visti.add(r["v"])
                yield normalizza_votazione(r, legislatura)

    def voti_del_giorno(self, legislatura: int, giorno: date) -> Iterator[VotoGrezzo]:
        prefisso = f"{SENATO_VOTAZIONE}{legislatura}-"
        for r in self.sparql.pagine(query_votazioni_del_giorno(giorno)):
            if r["v"].startswith(prefisso):
                archi = [{**x, "v": r["v"]} for x in self.sparql.pagine(query_archi_votazione(r["v"]))]
                yield from voti_da_archi(archi)

    def parlamentari(self, legislatura: int) -> Iterator[ParlamentareGrezzo]:
        visti: set[str] = set()
        for r in self.sparql.pagine(query_parlamentari(legislatura)):
            if r["s"] not in visti:
                visti.add(r["s"])
                yield ParlamentareGrezzo("senato", _id(RE_SENATORE, r["s"], "senatore"), r["nome"], r["cognome"])

    def adesioni(self, legislatura: int) -> Iterator[AdesioneGrezza]:
        visti: set[tuple[str, str, str]] = set()
        for r in self.sparql.pagine(query_adesioni(legislatura)):
            k = (r["s"], r["g"], r["inizio"])
            if k in visti:
                continue
            visti.add(k)
            yield AdesioneGrezza(
                "senato",
                _id(RE_SENATORE, r["s"], "senatore"),
                _id(RE_GRUPPO, r["g"], "gruppo"),
                data_iso(r["inizio"]),
                data_iso(r["fine"]) if r.get("fine") else None,
            )
