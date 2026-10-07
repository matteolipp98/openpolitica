"""Sonda degli open data (ADR 0002, 0025).

Verifica che le fonti gratuite previste dagli ADR rispondano e scopre la forma reale dei dati
(classi e proprietà SPARQL di Camera e Senato, gruppi della legislatura, identificativi dei leader).
Il rapporto serve a compilare content/gruppi.yaml e content/alias/*.yaml e a scrivere i connettori
e i loro test di contratto. Solo libreria standard: deve girare ovunque, anche in CI.

Uso: python -m op_workers.connettori.sonda_open_data [--uscita DIR] [--legislatura 19]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

UA = "openpolitica-sonda/0.1 (+https://github.com/matteolipp98/openpolitica)"
TIMEOUT = 180

CAMERA = "https://dati.camera.it/sparql"
SENATO = "https://dati.senato.it/sparql"

PREFISSI = """
PREFIX ocd: <http://dati.camera.it/ocd/>
PREFIX osr: <http://dati.senato.it/osr/>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""

# Cognomi dei leader del perimetro (content/perimetro.yaml)
LEADER = ["Meloni", "Schlein", "Salvini", "Conte", "Tajani", "Bonelli", "Fratoianni", "Lupi", "Calenda", "Renzi"]

# Endpoint HTTP delle altre fonti previste (ADR 0002, 0014, 0020)
ALTRE_FONTI = {
    "openpolis": "https://www.openpolis.it/",
    "istat_sdmx": "https://esploradati.istat.it/SDMXWS/rest/dataflow/IT1/all/latest?detail=allstubs",
    "istat_sdmx_legacy": "https://sdmx.istat.it/SDMXWS/rest/dataflow/IT1/all/latest?detail=allstubs",
    "eurostat": "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/une_rt_m?geo=IT&sex=T&age=TOTAL&unit=PC_ACT&s_adj=SA&lastTimePeriod=1",
    "gdelt_doc": "https://api.gdeltproject.org/api/v2/doc/doc?query=%22Giorgia%20Meloni%22&mode=artlist&maxrecords=1&format=json",
    "wayback_cdx": "https://web.archive.org/cdx/search/cdx?url=dait.interno.gov.it&limit=1&output=json",
    "programmi_interno": "https://dait.interno.gov.it/elezioni/trasparenza",
    "normattiva": "https://www.normattiva.it/",
    "gazzetta_ufficiale": "https://www.gazzettaufficiale.it/",
}


@dataclass
class Esito:
    nome: str
    ok: bool
    ms: int
    righe: list[dict[str, str]] = field(default_factory=list)
    errore: str | None = None
    query: str | None = None


def _get(url: str, accept: str) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})  # noqa: S310
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:  # noqa: S310 (URL fissi)
        return r.status, r.read()


def semplifica(bindings: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Riduce i binding SPARQL JSON a {variabile: valore}."""
    return [{k: v.get("value", "") for k, v in b.items()} for b in bindings]


def sparql(endpoint: str, nome: str, query: str, tentativi: int = 2) -> Esito:
    q = PREFISSI + query
    url = endpoint + "?" + urllib.parse.urlencode({"query": q, "format": "application/sparql-results+json"})
    inizio = time.monotonic()
    ultimo = ""
    for t in range(tentativi):
        try:
            _, corpo = _get(url, "application/sparql-results+json")
            dati = json.loads(corpo)
            return Esito(
                nome,
                True,
                int((time.monotonic() - inizio) * 1000),
                semplifica(dati["results"]["bindings"]),
                query=query.strip(),
            )
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError) as e:
            ultimo = f"{type(e).__name__}: {e}"
            time.sleep(2 * (t + 1))
    return Esito(nome, False, int((time.monotonic() - inizio) * 1000), errore=ultimo[:500], query=query.strip())


def http(nome: str, url: str, attese: tuple[int, ...] = (15, 45)) -> Esito:
    """GET semplice; su 429 (troppe richieste, tipico di GDELT) riprova dopo le attese indicate."""
    inizio = time.monotonic()
    errore = ""
    for i in range(len(attese) + 1):
        try:
            stato, corpo = _get(url, "*/*")
            riga = {"stato": str(stato), "byte": str(len(corpo)), "inizio": corpo[:200].decode("utf8", "replace")}
            return Esito(nome, 200 <= stato < 400, int((time.monotonic() - inizio) * 1000), [riga])
        except urllib.error.HTTPError as e:
            errore = f"HTTP {e.code}"
            if e.code != 429 or i == len(attese):
                break
            time.sleep(attese[i])
        except (urllib.error.URLError, TimeoutError) as e:
            errore = f"{type(e).__name__}: {e}"[:300]
            break
    return Esito(nome, False, int((time.monotonic() - inizio) * 1000), errore=errore)


def _filtro_cognomi(var: str) -> str:
    valori = ", ".join(f'"{c.upper()}"' for c in LEADER)
    return f"FILTER(UCASE(STR({var})) IN ({valori}))"


def query_camera(leg: int) -> dict[str, str]:
    legislatura = f"<http://dati.camera.it/ocd/legislatura.rdf/repubblica_{leg}>"
    return {
        "classi": "SELECT ?classe (COUNT(?s) AS ?n) WHERE { ?s a ?classe } GROUP BY ?classe ORDER BY DESC(?n) LIMIT 60",
        "proprieta_votazione": """
            SELECT ?p (COUNT(*) AS ?n) (SAMPLE(?o) AS ?esempio) WHERE {
              { SELECT ?s WHERE { ?s a ocd:votazione } LIMIT 50 } ?s ?p ?o
            } GROUP BY ?p ORDER BY ?p""",
        "proprieta_voto": """
            SELECT ?p (COUNT(*) AS ?n) (SAMPLE(?o) AS ?esempio) WHERE {
              { SELECT ?s WHERE { ?s a ocd:voto } LIMIT 50 } ?s ?p ?o
            } GROUP BY ?p ORDER BY ?p""",
        "proprieta_deputato": """
            SELECT ?p (COUNT(*) AS ?n) (SAMPLE(?o) AS ?esempio) WHERE {
              { SELECT ?s WHERE { ?s a ocd:deputato } LIMIT 50 } ?s ?p ?o
            } GROUP BY ?p ORDER BY ?p""",
        "proprieta_gruppo": """
            SELECT ?p (COUNT(*) AS ?n) (SAMPLE(?o) AS ?esempio) WHERE {
              { SELECT ?s WHERE { ?s a ocd:gruppoParlamentare } LIMIT 50 } ?s ?p ?o
            } GROUP BY ?p ORDER BY ?p""",
        "votazioni_legislatura": f"""
            SELECT (COUNT(?v) AS ?n) (MIN(?d) AS ?prima) (MAX(?d) AS ?ultima) WHERE {{
              ?v a ocd:votazione ; ocd:rif_leg {legislatura} ; dc:date ?d }}""",
        "esempio_votazione": f"""
            SELECT ?v ?p ?o WHERE {{
              {{ SELECT ?v WHERE {{ ?v a ocd:votazione ; ocd:rif_leg {legislatura} ; dc:date ?d }}
                  ORDER BY DESC(?d) LIMIT 1 }}
              ?v ?p ?o }}""",
        "gruppi_legislatura": f"""
            SELECT DISTINCT ?g ?nome ?sigla WHERE {{
              ?g a ocd:gruppoParlamentare ; ocd:rif_leg {legislatura} .
              OPTIONAL {{ ?g rdfs:label ?nome }} OPTIONAL {{ ?g dcterms:alternative ?sigla }}
            }} ORDER BY ?nome""",
        "leader": f"""
            SELECT DISTINCT ?d ?nome ?cognome WHERE {{
              ?d a ocd:deputato ; ocd:rif_leg {legislatura} ; foaf:surname ?cognome ; foaf:firstName ?nome .
              {_filtro_cognomi("?cognome")} }} ORDER BY ?cognome""",
    }


def query_senato(leg: int) -> dict[str, str]:
    # La votazione ha URI http://dati.senato.it/votazione/<leg>-<seduta>-<numero>: si filtra sul prefisso.
    pref = f"http://dati.senato.it/votazione/{leg}-"
    voto = "<http://dati.senato.it/votazione/19-167-42>"
    filtro_leader = ", ".join(f"<http://dati.senato.it/senatore/{i}>" for i in (25407, 30742, 30110))
    return {
        "classi": "SELECT ?classe (COUNT(?s) AS ?n) WHERE { ?s a ?classe } GROUP BY ?classe ORDER BY DESC(?n) LIMIT 60",
        "votazioni_legislatura": f"""
            SELECT (COUNT(?v) AS ?n) WHERE {{ ?v a osr:Votazione . FILTER(STRSTARTS(STR(?v), "{pref}")) }}""",
        "predicati_votazione": f"SELECT DISTINCT ?p WHERE {{ {voto} ?p ?o }}",
        "conteggi_voto_esempio": f"""
            SELECT ?p (COUNT(?o) AS ?n) WHERE {{ {voto} ?p ?o . FILTER(isIRI(?o)) }} GROUP BY ?p""",
        "seduta": f"SELECT ?p ?o WHERE {{ {voto} osr:seduta ?s . ?s ?p ?o }}",
        "oggetto": f"SELECT ?p ?o WHERE {{ {voto} osr:oggetto ?s . ?s ?p ?o }}",
        "oggetto_atto": f"""
            SELECT ?p2 ?o2 WHERE {{ {voto} osr:oggetto ?s . ?s ?p ?x . ?x ?p2 ?o2 .
              FILTER(isIRI(?x) && STRSTARTS(STR(?x), "http://dati.senato.it/")) }} LIMIT 80""",
        "senatore": "SELECT ?p ?o WHERE { <http://dati.senato.it/senatore/30742> ?p ?o }",
        # Il server del Senato rifiuta VALUES (HTTP 400): si filtra con IN.
        "mandati_leader": f"""
            SELECT ?s ?m ?q ?o WHERE {{
              ?s ?p ?m . ?m a ocd:mandatoSenato . ?m ?q ?o . FILTER(?s IN ({filtro_leader})) }}""",
        "adesioni_leader": f"""
            SELECT ?s ?g ?inizio ?fine WHERE {{
              ?s ocd:aderisce ?a . ?a osr:legislatura {leg} ; osr:gruppo ?g ; osr:inizio ?inizio .
              OPTIONAL {{ ?a osr:fine ?fine }} FILTER(?s IN ({filtro_leader})) }}""",
        "gruppo_esempio": "SELECT ?p ?o WHERE { <http://dati.senato.it/gruppo/49> ?p ?o }",
        # Solo le denominazioni in vigore nella legislatura (iniziate dopo il suo avvio o ancora aperte)
        "gruppi_legislatura": f"""
            SELECT DISTINCT ?g ?titolo ?breve ?inizio ?fine WHERE {{
              ?a a ocd:adesioneGruppo ; osr:legislatura {leg} ; osr:gruppo ?g .
              ?g osr:denominazione ?d . ?d osr:titolo ?titolo ; osr:inizio ?inizio .
              OPTIONAL {{ ?d osr:titoloBreve ?breve }} OPTIONAL {{ ?d osr:fine ?fine }}
              FILTER(STR(?inizio) >= "2022-10-13" || !BOUND(?fine))
            }} ORDER BY ?g ?inizio""",
        "astenuti_individuali": f"""
            SELECT (COUNT(*) AS ?n) WHERE {{ ?v osr:astenuto ?s . FILTER(STRSTARTS(STR(?v), "{pref}")) }}""",
        "duplicati_voto_esempio": f"""
            SELECT (COUNT(?s) AS ?righe) (COUNT(DISTINCT ?s) AS ?distinti) WHERE {{ {voto} osr:favorevole ?s }}""",
        "ddl_esempio": "SELECT ?p ?o WHERE { <http://dati.senato.it/ddl/58039> ?p ?o }",
    }


def query_camera_approfondimenti(leg: int) -> dict[str, str]:
    legislatura = f"<http://dati.camera.it/ocd/legislatura.rdf/repubblica_{leg}>"
    leader = " ".join(
        f"<http://dati.camera.it/ocd/deputato.rdf/d{i}_{leg}>"
        for i in (302080, 307926, 305880, 300447, 302103, 308930, 308838)
    )
    return {
        "tipi_votazioni": f"""
            SELECT ?tipo ?finale (COUNT(?v) AS ?n) (COUNT(?atto) AS ?con_atto) WHERE {{
              ?v a ocd:votazione ; ocd:rif_leg {legislatura} ; dc:type ?tipo ; ocd:votazioneFinale ?finale .
              OPTIONAL {{ ?v ocd:rif_attoCamera ?atto }}
            }} GROUP BY ?tipo ?finale ORDER BY DESC(?n)""",
        "finali_con_atto": f"""
            SELECT ?v ?data ?titolo ?descr ?atto ?titolo_atto ?fav ?con ?ast WHERE {{
              ?v a ocd:votazione ; ocd:rif_leg {legislatura} ; ocd:votazioneFinale 1 ; dc:date ?data ;
                 dc:title ?titolo ; ocd:favorevoli ?fav ; ocd:contrari ?con ; ocd:astenuti ?ast .
              OPTIONAL {{ ?v ocd:rif_attoCamera ?atto . OPTIONAL {{ ?atto dc:title ?titolo_atto }} }}
              OPTIONAL {{ ?v dc:description ?descr }}
            }} ORDER BY DESC(?data) LIMIT 15""",
        "tipi_voto_esempio": """
            SELECT ?tipo ?descr (COUNT(?x) AS ?n) WHERE {
              ?x a ocd:voto ; ocd:rif_votazione <http://dati.camera.it/ocd/votazione.rdf/vs19_718_011> ; dc:type ?tipo .
              OPTIONAL { ?x dc:description ?descr }
            } GROUP BY ?tipo ?descr""",
        "storia_gruppo_azione": """
            SELECT ?d ?p ?o WHERE {
              <http://dati.camera.it/ocd/gruppoParlamentare.rdf/gr4135> ocd:denominazione ?d . ?d ?p ?o }""",
        "adesioni_leader": f"""
            SELECT ?d ?p ?o WHERE {{ VALUES ?d {{ {leader} }} ?d ocd:aderisce ?a . ?a ?p ?o }}""",
        "deputato_esempio": f"SELECT ?p ?o WHERE {{ <http://dati.camera.it/ocd/deputato.rdf/d302103_{leg}> ?p ?o }}",
        "atto_esempio": f"SELECT ?p ?o WHERE {{ <http://dati.camera.it/ocd/attocamera.rdf/ac{leg}_3118> ?p ?o }}",
        "duplicati": f"""
            SELECT (COUNT(?v) AS ?righe) (COUNT(DISTINCT ?v) AS ?distinte) WHERE {{
              ?v a ocd:votazione ; ocd:rif_leg {legislatura} }}""",
        "duplicati_voti_esempio": """
            SELECT (COUNT(?x) AS ?righe) (COUNT(DISTINCT ?x) AS ?distinti) WHERE {
              ?x a ocd:voto ; ocd:rif_votazione <http://dati.camera.it/ocd/votazione.rdf/vs19_718_011> }""",
    }


def esegui(leg: int) -> dict[str, Any]:
    rapporto: dict[str, Any] = {
        "eseguita_il": datetime.now(UTC).isoformat(timespec="seconds"),
        "legislatura": leg,
        "camera": {},
        "senato": {},
        "altre_fonti": {},
    }
    for nome, q in query_camera(leg).items():
        rapporto["camera"][nome] = asdict(sparql(CAMERA, nome, q))
    for nome, q in query_camera_approfondimenti(leg).items():
        rapporto["camera"][nome] = asdict(sparql(CAMERA, nome, q))
    for nome, q in query_senato(leg).items():
        rapporto["senato"][nome] = asdict(sparql(SENATO, nome, q))
    for nome, url in ALTRE_FONTI.items():
        rapporto["altre_fonti"][nome] = asdict(http(nome, url))
    return rapporto


def in_markdown(r: dict[str, Any], max_righe: int = 60) -> str:
    out = [f"# Sonda open data — {r['eseguita_il']} — legislatura {r['legislatura']}\n"]
    for sezione in ("camera", "senato", "altre_fonti"):
        out.append(f"\n## {sezione}\n")
        for nome, e in r[sezione].items():
            stato = "OK" if e["ok"] else "ERRORE"
            out.append(f"\n### {nome} — {stato} ({e['ms']} ms, {len(e['righe'])} righe)\n")
            if e["errore"]:
                out.append(f"\n`{e['errore']}`\n")
            if e["righe"]:
                chiavi = list(e["righe"][0].keys())
                out.append("\n| " + " | ".join(chiavi) + " |\n|" + "---|" * len(chiavi) + "\n")
                for riga in e["righe"][:max_righe]:
                    celle = [str(riga.get(k, "")).replace("|", "\\|").replace("\n", " ")[:140] for k in chiavi]
                    out.append("| " + " | ".join(celle) + " |\n")
                if len(e["righe"]) > max_righe:
                    out.append(f"\n… altre {len(e['righe']) - max_righe} righe nel JSON\n")
    return "".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--uscita", default="sonde")
    ap.add_argument("--legislatura", type=int, default=19)
    a = ap.parse_args(argv)

    r = esegui(a.legislatura)
    cartella = Path(a.uscita)
    cartella.mkdir(parents=True, exist_ok=True)
    (cartella / "rapporto.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf8")
    md = in_markdown(r)
    (cartella / "rapporto.md").write_text(md, encoding="utf8")
    print(md)
    if riepilogo := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(riepilogo, "a", encoding="utf8") as f:
            f.write(md[:900_000])

    # Esce con errore solo se un intero endpoint SPARQL è irraggiungibile: le singole query sono esplorative.
    giu = [s for s in ("camera", "senato") if not any(e["ok"] for e in r[s].values())]
    if giu:
        print(f"Endpoint irraggiungibili: {', '.join(giu)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
