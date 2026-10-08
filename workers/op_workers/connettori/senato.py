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
BLOCCO = 20  # votazioni per richiesta: oltre, le righe superano una pagina

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


def _numero_fase(fase: str) -> tuple[int, str]:
    m = re.search(r"\d+", fase)
    return (int(m.group()) if m else 0, fase)


def scegli_atto(righe: list[dict[str, str]]) -> tuple[str | None, str | None]:
    """(atto_ref, atto_titolo) di una votazione dalle sue righe, una per documento collegato (osr:relativoA).

    Una votazione finale può riguardare più disegni di legge esaminati insieme (#74): conta quello approvato,
    gli altri sono "assorbito". Si ignorano i documenti senza numero di fase (petizioni, relazioni) se c'è
    anche un disegno di legge. Se restano più testi non assorbiti (testo unificato, "appr. in t.u."), il
    titolo del testo votato non è nei dati: atto_titolo resta vuoto e la votazione non diventa una domanda.
    """
    atti: dict[str, dict[str, str]] = {}
    for r in righe:
        if r.get("ddl") or r.get("fase") or r.get("titolo"):
            atti.setdefault(r.get("ddl") or r.get("fase") or r.get("titolo", ""), r)
    voci = list(atti.values())
    con_fase = [a for a in voci if (a.get("fase") or "").strip()]
    if con_fase:
        voci = con_fase
    if len(voci) > 1:
        voci = [a for a in voci if (a.get("stato") or "").strip().lower() != "assorbito"] or voci
    if not voci:
        return None, None
    if len(voci) > 1:
        fasi = sorted({a["fase"].strip() for a in voci}, key=_numero_fase)
        return ", ".join(fasi), None
    a = voci[0]
    return (a.get("fase") or "").strip() or None, (a.get("titolo") or "").strip() or None


def normalizza_votazione(riga: dict[str, str], leg: int, atti: list[dict[str, str]] | None = None) -> VotazioneGrezza:
    """Una votazione dalla sua prima riga; atti = tutte le sue righe, per scegliere il documento votato."""
    etichetta = (riga.get("label") or "").strip() or None
    e = (etichetta or "").lower()
    atto_ref, atto_titolo = scegli_atto(atti or [riga])
    return VotazioneGrezza(
        ramo="senato",
        legislatura=leg,
        id_esterno=_id(RE_VOTAZIONE, riga["v"], "votazione"),
        data=data_iso(riga["data"]),
        tipo=etichetta,
        titolo=etichetta,
        descrizione=(riga.get("esito") or "").strip() or None,
        atto_ref=atto_ref,  # es. 'S.1056'
        atto_titolo=atto_titolo,
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
SELECT DISTINCT ?v ?data ?label ?fav ?con ?ast ?esito ?tipoVot ?ddl ?titolo ?fase ?stato WHERE {{
  ?v a osr:Votazione ; osr:legislatura {leg} ; osr:seduta ?s ; osr:favorevoli ?fav ; osr:contrari ?con .
  ?s osr:dataSeduta ?data .
  OPTIONAL {{ ?v osr:astenuti ?ast }} OPTIONAL {{ ?v rdfs:label ?label }} OPTIONAL {{ ?v osr:esito ?esito }}
  OPTIONAL {{ ?v osr:tipoVotazione ?tipoVot }}
  OPTIONAL {{ ?v osr:oggetto ?o . ?o osr:relativoA ?ddl .
             OPTIONAL {{ ?ddl osr:titolo ?titolo }} OPTIONAL {{ ?ddl osr:fase ?fase }}
             OPTIONAL {{ ?ddl osr:statoDdl ?stato }} }}
  FILTER(STR(?data) >= "{dal.isoformat()}" && STR(?data) <= "{al.isoformat()}")
}} ORDER BY ?data ?v ?ddl"""


def query_atti_finali(leg: int) -> str:
    """I documenti collegati a tutte le votazioni finali della legislatura: una sola richiesta (~350 righe)."""
    return f"""
SELECT DISTINCT ?v ?ddl ?titolo ?fase ?stato WHERE {{
  ?v a osr:Votazione ; osr:legislatura {leg} ; rdfs:label ?l ; osr:oggetto ?o . ?o osr:relativoA ?ddl .
  OPTIONAL {{ ?ddl osr:titolo ?titolo }} OPTIONAL {{ ?ddl osr:fase ?fase }} OPTIONAL {{ ?ddl osr:statoDdl ?stato }}
  FILTER(STRSTARTS(LCASE(STR(?l)), "votazione finale"))
}} ORDER BY ?v ?ddl"""


def query_votazioni_del_giorno(giorno: date) -> str:
    return f"""
SELECT DISTINCT ?v WHERE {{
  ?v a osr:Votazione ; osr:seduta ?s . ?s osr:dataSeduta ?data .
  FILTER(STR(?data) = "{giorno.isoformat()}")
}} ORDER BY ?v"""


def query_archi_votazioni(uris: list[str]) -> str:
    """I voti di un blocco di votazioni: la query su un giorno intero è troppo pesante (HTTP 502).

    Il server rifiuta VALUES e BIND (HTTP 400): le votazioni si filtrano con FILTER(?v IN (...)).
    Un blocco di 20 costa quanto una votazione sola (misura in #54: 1,6 s, voti identici).
    """
    archi = ", ".join(f"osr:{a}" for a in ARCHI)
    lista = ", ".join(f"<{u}>" for u in uris)
    return f"""
SELECT DISTINCT ?v ?p ?sen WHERE {{
  ?v ?p ?sen . FILTER(?v IN ({lista})) FILTER(?p IN ({archi}))
}} ORDER BY ?v ?sen ?p"""


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
        # Il Senato blocca (403) chi fa richieste troppo ravvicinate: almeno un secondo e mezzo tra l'una e l'altra
        self.sparql = sparql or ClientSparql(ENDPOINT, pausa=1.5)

    def votazioni(self, legislatura: int, dal: date) -> Iterator[VotazioneGrezza]:
        per_votazione: dict[str, list[dict[str, str]]] = {}  # in ordine di data: i dict tengono l'ordine
        for inizio, fine in finestre_mensili(dal):
            for r in self.sparql.pagine(query_votazioni(legislatura, inizio, fine), pagina=1000):
                per_votazione.setdefault(r["v"], []).append(r)
        for righe in per_votazione.values():
            yield normalizza_votazione(righe[0], legislatura, righe)

    def atti_votazioni_finali(self, legislatura: int) -> dict[str, tuple[str | None, str | None]]:
        """{id votazione: (atto_ref, atto_titolo)} per le votazioni finali: corregge quelle già salvate (#74)."""
        per_votazione: dict[str, list[dict[str, str]]] = {}
        for r in self.sparql.pagine(query_atti_finali(legislatura), pagina=1000):
            per_votazione.setdefault(_id(RE_VOTAZIONE, r["v"], "votazione"), []).append(r)
        return {v: scegli_atto(righe) for v, righe in per_votazione.items()}

    def voti_del_giorno(self, legislatura: int, giorno: date) -> Iterator[VotoGrezzo]:
        prefisso = f"{SENATO_VOTAZIONE}{legislatura}-"
        uris = [r["v"] for r in self.sparql.pagine(query_votazioni_del_giorno(giorno)) if r["v"].startswith(prefisso)]
        for i in range(0, len(uris), BLOCCO):
            yield from voti_da_archi(self.sparql.pagine(query_archi_votazioni(uris[i : i + BLOCCO])))

    def voti_delle_votazioni(self, legislatura: int, giorno: date, ids: list[str]) -> Iterator[VotoGrezzo]:
        """Solo le votazioni indicate: l'import le chiede a blocchi e salta quelle già salvate."""
        uris = [f"{SENATO_VOTAZIONE}{vid}" for vid in ids]
        for i in range(0, len(uris), BLOCCO):
            yield from voti_da_archi(self.sparql.pagine(query_archi_votazioni(uris[i : i + BLOCCO])))

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
