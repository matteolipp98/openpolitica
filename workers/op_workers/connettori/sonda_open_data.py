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
TIMEOUT = 90

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
    "openparlamento_api": "https://service.openpolis.it/",
    "istat_sdmx": "https://esploradati.istat.it/SDMXWS/rest/dataflow/IT1/all/latest?detail=allstubs",
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


def http(nome: str, url: str) -> Esito:
    inizio = time.monotonic()
    try:
        stato, corpo = _get(url, "*/*")
        return Esito(
            nome,
            200 <= stato < 400,
            int((time.monotonic() - inizio) * 1000),
            [{"stato": str(stato), "byte": str(len(corpo)), "inizio": corpo[:200].decode("utf8", "replace")}],
        )
    except urllib.error.HTTPError as e:
        return Esito(nome, False, int((time.monotonic() - inizio) * 1000), errore=f"HTTP {e.code}")
    except (urllib.error.URLError, TimeoutError) as e:
        return Esito(nome, False, int((time.monotonic() - inizio) * 1000), errore=f"{type(e).__name__}: {e}"[:300])


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
    return {
        "classi": "SELECT ?classe (COUNT(?s) AS ?n) WHERE { ?s a ?classe } GROUP BY ?classe ORDER BY DESC(?n) LIMIT 60",
        "proprieta_votazione": """
            SELECT ?p (COUNT(*) AS ?n) (SAMPLE(?o) AS ?esempio) WHERE {
              { SELECT ?s WHERE { ?s a osr:Votazione } LIMIT 50 } ?s ?p ?o
            } GROUP BY ?p ORDER BY ?p""",
        "proprieta_senatore": """
            SELECT ?p (COUNT(*) AS ?n) (SAMPLE(?o) AS ?esempio) WHERE {
              { SELECT ?s WHERE { ?s a osr:Senatore } LIMIT 50 } ?s ?p ?o
            } GROUP BY ?p ORDER BY ?p""",
        "proprieta_gruppo": """
            SELECT ?p (COUNT(*) AS ?n) (SAMPLE(?o) AS ?esempio) WHERE {
              { SELECT ?s WHERE { ?s a osr:Gruppo } LIMIT 50 } ?s ?p ?o
            } GROUP BY ?p ORDER BY ?p""",
        "votazioni_legislatura": f"""
            SELECT (COUNT(?v) AS ?n) (MIN(?d) AS ?prima) (MAX(?d) AS ?ultima) WHERE {{
              ?v a osr:Votazione ; osr:legislatura {leg} ; osr:dataSeduta ?d }}""",
        "esempio_votazione": f"""
            SELECT ?v ?p ?o WHERE {{
              {{ SELECT ?v WHERE {{ ?v a osr:Votazione ; osr:legislatura {leg} }} LIMIT 1 }}
              ?v ?p ?o }}""",
        "gruppi_legislatura": f"""
            SELECT DISTINCT ?g ?nome WHERE {{
              ?g a osr:Gruppo . ?g ?pn ?nome . FILTER(isLiteral(?nome))
              ?adesione osr:gruppo ?g ; osr:legislatura {leg} .
            }} LIMIT 200""",
        "leader": f"""
            SELECT DISTINCT ?s ?nome ?cognome WHERE {{
              ?s a osr:Senatore ; foaf:lastName ?cognome ; foaf:firstName ?nome .
              {_filtro_cognomi("?cognome")}
            }} ORDER BY ?cognome""",
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
