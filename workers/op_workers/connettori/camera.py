"""Connettore Camera dei deputati: SPARQL su dati.camera.it (struttura in docs/fonti-open-data.md).

Il dataset della Camera contiene ogni votazione e ogni voto due volte: tutte le query usano
DISTINCT e i risultati vengono comunque deduplicati per URI.
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

ENDPOINT = "https://dati.camera.it/sparql"

RE_VOTAZIONE = re.compile(r"votazione\.rdf/(vs\d+_\d+_\d+)$")
RE_DEPUTATO = re.compile(r"deputato\.rdf/d(\d+)_\d+$")
RE_GRUPPO = re.compile(r"gruppoParlamentare\.rdf/(gr\d+)$")
RE_ATTO = re.compile(r"attocamera\.rdf/ac\d+_(\w+)$")
RE_ATTO_DESCR = re.compile(r"\b(?:DDL|PDL|PDLC|DOC)\s+(\d+)", re.IGNORECASE)


def legislatura_uri(leg: int) -> str:
    return f"<http://dati.camera.it/ocd/legislatura.rdf/repubblica_{leg}>"


def data_camera(s: str) -> date:
    """Le date della Camera sono stringhe AAAAMMGG."""
    if not re.fullmatch(r"\d{8}", s):
        raise DatoInatteso(f"data Camera non valida: {s!r}")
    return date(int(s[:4]), int(s[4:6]), int(s[6:]))


def _bool(s: str | None) -> bool:
    return s in ("1", "true", "True")


def _id(regex: re.Pattern[str], uri: str, cosa: str) -> str:
    m = regex.search(uri)
    if not m:
        raise DatoInatteso(f"{cosa}: URI inattesa {uri!r}")
    return m.group(1)


def espressione(tipo: str, descrizione: str | None) -> Espressione:
    """dc:type e dc:description del voto → core.espressione. Valori sconosciuti: errore, non default."""
    t, d = tipo.strip().lower(), (descrizione or "").strip().lower()
    if t == "favorevole":
        return "favorevole"
    if t == "contrario":
        return "contrario"
    if t == "astensione":
        return "astenuto"
    if t == "ha votato":  # voto segreto: si sa solo che ha partecipato
        return "votante_segreto"
    if t == "non ha votato":
        if d in ("", "non ha votato"):
            return "non_votante"
        if d == "non ha partecipato":
            return "assente"
        if d == "in missione":
            return "in_missione"
        if d == "presidente di turno":
            return "presidente"
    raise DatoInatteso(f"voto Camera sconosciuto: tipo={tipo!r} descrizione={descrizione!r}")


def atto_ref(uri_atto: str | None, descrizione: str | None) -> str | None:
    """'C.3118' dall'URI dell'atto, oppure dal numero in dc:description (es. 'DDL 3118 - VOTO FINALE')."""
    if uri_atto and (m := RE_ATTO.search(uri_atto)):
        return f"C.{m.group(1)}"
    if descrizione and (m := RE_ATTO_DESCR.search(descrizione)):
        return f"C.{m.group(1)}"
    return None


def normalizza_votazione(riga: dict[str, str], leg: int) -> VotazioneGrezza:
    titolo = (riga.get("titolo") or "").strip() or None
    descr = (riga.get("descr") or "").strip() or None
    return VotazioneGrezza(
        ramo="camera",
        legislatura=leg,
        id_esterno=_id(RE_VOTAZIONE, riga["v"], "votazione"),
        data=data_camera(riga["data"]),
        tipo=(riga.get("tipo") or "").strip() or None,
        titolo=titolo,
        descrizione=descr,
        atto_ref=atto_ref(riga.get("atto"), descr),
        atto_titolo=(riga.get("atto_titolo") or "").strip() or None,
        finale=_bool(riga.get("finale")),
        fiducia=_bool(riga.get("fiducia")),
        segreta=_bool(riga.get("segreta")),
        favorevoli=int(riga["fav"]),
        contrari=int(riga["con"]),
        astenuti=int(riga["ast"]),
        approvata=None if riga.get("approvato") is None else _bool(riga.get("approvato")),
        url=riga.get("url") or riga["v"],
    )


def normalizza_voto(riga: dict[str, str]) -> VotoGrezzo:
    gruppo = riga.get("gruppo")
    return VotoGrezzo(
        id_votazione_esterno=_id(RE_VOTAZIONE, riga["v"], "votazione"),
        id_persona_esterno=_id(RE_DEPUTATO, riga["dep"], "deputato"),
        espressione=espressione(riga["tipo"], riga.get("descr")),
        id_gruppo_esterno=_id(RE_GRUPPO, gruppo, "gruppo") if gruppo else None,
    )


def query_votazioni(leg: int, dal: date, al: date) -> str:
    return f"""
SELECT DISTINCT ?v ?data ?tipo ?titolo ?descr ?finale ?fiducia ?segreta ?fav ?con ?ast ?approvato ?url
                ?atto ?atto_titolo
WHERE {{
  ?v a ocd:votazione ; ocd:rif_leg {legislatura_uri(leg)} ; dc:date ?data ; ocd:votazioneFinale ?finale ;
     ocd:favorevoli ?fav ; ocd:contrari ?con ; ocd:astenuti ?ast .
  OPTIONAL {{ ?v dc:type ?tipo }} OPTIONAL {{ ?v dc:title ?titolo }} OPTIONAL {{ ?v dc:description ?descr }}
  OPTIONAL {{ ?v ocd:richiestaFiducia ?fiducia }} OPTIONAL {{ ?v ocd:votazioneSegreta ?segreta }}
  OPTIONAL {{ ?v ocd:approvato ?approvato }} OPTIONAL {{ ?v dc:relation ?url }}
  OPTIONAL {{ ?v ocd:rif_attoCamera ?atto . OPTIONAL {{ ?atto rdfs:label ?atto_titolo }} }}
  FILTER(STR(?data) >= "{dal:%Y%m%d}" && STR(?data) <= "{al:%Y%m%d}")
}} ORDER BY ?data ?v"""


def query_voti_del_giorno(leg: int, giorno: date) -> str:
    return f"""
SELECT DISTINCT ?x ?v ?dep ?tipo ?descr ?gruppo WHERE {{
  ?v a ocd:votazione ; ocd:rif_leg {legislatura_uri(leg)} ; dc:date ?data .
  FILTER(STR(?data) = "{giorno:%Y%m%d}")
  ?x a ocd:voto ; ocd:rif_votazione ?v ; ocd:rif_deputato ?dep ; dc:type ?tipo .
  OPTIONAL {{ ?x dc:description ?descr }} OPTIONAL {{ ?x ocd:rif_gruppoParlamentare ?gruppo }}
}} ORDER BY ?x"""


def query_parlamentari(leg: int) -> str:
    return f"""
SELECT DISTINCT ?d ?nome ?cognome WHERE {{
  ?d a ocd:deputato ; ocd:rif_leg {legislatura_uri(leg)} ; foaf:firstName ?nome ; foaf:surname ?cognome .
}} ORDER BY ?d"""


def query_adesioni(leg: int) -> str:
    return f"""
SELECT DISTINCT ?d ?g ?inizio ?fine WHERE {{
  ?d a ocd:deputato ; ocd:rif_leg {legislatura_uri(leg)} ; ocd:aderisce ?a .
  ?a ocd:rif_gruppoParlamentare ?g ; ocd:startDate ?inizio .
  OPTIONAL {{ ?a ocd:endDate ?fine }}
}} ORDER BY ?d ?inizio"""


def _unici(righe: list[dict[str, str]], chiave: str) -> list[dict[str, str]]:
    """Una riga per URI: i duplicati del dataset (e le righe moltiplicate dagli OPTIONAL) si scartano."""
    visti: set[str] = set()
    out = []
    for r in righe:
        if r[chiave] not in visti:
            visti.add(r[chiave])
            out.append(r)
    return out


class ConnettoreCamera:
    ramo = "camera"

    def __init__(self, sparql: ClientSparql | None = None) -> None:
        self.sparql = sparql or ClientSparql(ENDPOINT)

    def votazioni(self, legislatura: int, dal: date) -> Iterator[VotazioneGrezza]:
        visti: set[str] = set()
        for inizio, fine in finestre_mensili(dal):
            for r in _unici(self.sparql.pagine(query_votazioni(legislatura, inizio, fine), pagina=1000), "v"):
                if r["v"] not in visti:
                    visti.add(r["v"])
                    yield normalizza_votazione(r, legislatura)

    def voti_del_giorno(self, legislatura: int, giorno: date) -> Iterator[VotoGrezzo]:
        for r in _unici(self.sparql.pagine(query_voti_del_giorno(legislatura, giorno)), "x"):
            yield normalizza_voto(r)

    def parlamentari(self, legislatura: int) -> Iterator[ParlamentareGrezzo]:
        for r in _unici(self.sparql.pagine(query_parlamentari(legislatura)), "d"):
            yield ParlamentareGrezzo(
                "camera", _id(RE_DEPUTATO, r["d"], "deputato"), r["nome"].title(), r["cognome"].title()
            )

    def adesioni(self, legislatura: int) -> Iterator[AdesioneGrezza]:
        visti: set[tuple[str, str, str]] = set()
        for r in self.sparql.pagine(query_adesioni(legislatura)):
            k = (r["d"], r["g"], r["inizio"])
            if k in visti:
                continue
            visti.add(k)
            yield AdesioneGrezza(
                "camera",
                _id(RE_DEPUTATO, r["d"], "deputato"),
                _id(RE_GRUPPO, r["g"], "gruppo"),
                data_camera(r["inizio"]),
                data_camera(r["fine"]) if r.get("fine") else None,
            )
