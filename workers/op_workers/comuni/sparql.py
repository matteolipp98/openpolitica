"""Client SPARQL minimale per gli endpoint Virtuoso di Camera e Senato."""

from __future__ import annotations

import time

import httpx

UA = "openpolitica/0.1 (+https://github.com/matteolipp98/openpolitica)"

PREFISSI = """\
PREFIX ocd: <http://dati.camera.it/ocd/>
PREFIX osr: <http://dati.senato.it/osr/>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""


class ErroreSparql(RuntimeError):
    pass


class ClientSparql:
    def __init__(self, endpoint: str, client: httpx.Client | None = None, tentativi: int = 4, attesa: float = 2.0):
        self.endpoint = endpoint
        self.http = client or httpx.Client(timeout=120, headers={"User-Agent": UA})
        self.tentativi = tentativi
        self.attesa = attesa

    def select(self, query: str) -> list[dict[str, str]]:
        """Esegue una SELECT e restituisce le righe come {variabile: valore}. Riprova su errori temporanei."""
        ultimo = ""
        for i in range(self.tentativi):
            try:
                r = self.http.get(
                    self.endpoint,
                    params={"query": PREFISSI + query, "format": "application/sparql-results+json"},
                    headers={"Accept": "application/sparql-results+json"},
                )
                if r.status_code in (429, 500, 502, 503, 504):
                    ultimo = f"HTTP {r.status_code}"
                else:
                    r.raise_for_status()
                    return [{k: v.get("value", "") for k, v in b.items()} for b in r.json()["results"]["bindings"]]
            except (httpx.TransportError, ValueError, KeyError) as e:
                ultimo = f"{type(e).__name__}: {e}"
            except httpx.HTTPStatusError as e:  # 4xx: query sbagliata, inutile riprovare
                raise ErroreSparql(f"{self.endpoint}: HTTP {e.response.status_code}") from e
            time.sleep(self.attesa * 2**i)
        raise ErroreSparql(f"{self.endpoint}: {ultimo}")

    def pagine(self, query: str, pagina: int = 5000) -> list[dict[str, str]]:
        """Esegue la query a pagine. La query deve avere un ORDER BY stabile e non avere LIMIT/OFFSET."""
        righe: list[dict[str, str]] = []
        offset = 0
        while True:
            blocco = self.select(f"{query}\nLIMIT {pagina} OFFSET {offset}")
            righe.extend(blocco)
            if len(blocco) < pagina:
                return righe
            offset += pagina
