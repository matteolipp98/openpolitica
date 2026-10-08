"""Richieste educate: robots.txt, una pausa tra due richieste allo stesso sito, opposizione al text and data mining.

ADR 0003: il crawler rispetta robots.txt e i meccanismi di opt-out per il text and data mining (TDMRep:
intestazione o meta `tdm-reservation`, file /.well-known/tdmrep.json).
"""

from __future__ import annotations

import fnmatch
import re
import time
from collections.abc import Callable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx

UA = "openpolitica/0.1 (+https://github.com/matteolipp98/openpolitica)"
AGENTE = "openpolitica"  # il nome con cui ci cercano le regole di robots.txt
PAUSA = 2.0  # secondi tra due richieste allo stesso sito
META_TDM = re.compile(rb"<meta[^>]+name=[\"']tdm-reservation[\"'][^>]+content=[\"']1[\"']", re.IGNORECASE)


class NonPermesso(Exception):
    """robots.txt non ci permette di leggere questo indirizzo."""


def dominio(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def normalizza_url(url: str) -> str:
    """Senza frammento e senza i parametri di tracciamento (utm_*): lo stesso articolo ha un solo indirizzo."""
    p = urlsplit(url.strip())
    query = urlencode([(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if not k.startswith("utm_")])
    return urlunsplit((p.scheme, p.netloc.lower(), p.path, query, ""))


class Rete:
    def __init__(
        self,
        client: httpx.Client | None = None,
        pausa: float = PAUSA,
        dormi: Callable[[float], None] = time.sleep,
        orologio: Callable[[], float] = time.monotonic,
    ):
        self.client = client or httpx.Client(headers={"User-Agent": UA}, timeout=30, follow_redirects=True)
        self.pausa, self._dormi, self._orologio = pausa, dormi, orologio
        self._ultima: dict[str, float] = {}
        self._robots: dict[str, RobotFileParser | bool] = {}
        self._tdmrep: dict[str, list[dict]] = {}

    def _get(self, url: str) -> httpx.Response:
        host = dominio(url)
        if host in self._ultima:
            attesa = self.pausa - (self._orologio() - self._ultima[host])
            if attesa > 0:
                self._dormi(attesa)
        try:
            return self.client.get(url)
        finally:
            self._ultima[host] = self._orologio()

    def permesso(self, url: str) -> bool:
        p = urlsplit(url)
        radice = f"{p.scheme}://{p.netloc}"
        if radice not in self._robots:
            try:
                r = self._get(radice + "/robots.txt")
            except httpx.HTTPError:
                self._robots[radice] = False  # non sappiamo cosa permette: non leggiamo
            else:
                if r.status_code in (401, 403):
                    self._robots[radice] = False
                elif r.status_code >= 400:
                    self._robots[radice] = True  # niente robots.txt: nessun divieto
                else:
                    rp = RobotFileParser()
                    rp.parse(r.text.splitlines())
                    self._robots[radice] = rp
        regole = self._robots[radice]
        return regole if isinstance(regole, bool) else regole.can_fetch(AGENTE, url)

    def scarica(self, url: str) -> httpx.Response:
        if not self.permesso(url):
            raise NonPermesso(url)
        r = self._get(url)
        r.raise_for_status()
        return r

    def tdm_riservato(self, risposta: httpx.Response) -> bool:
        """L'editore si oppone al text and data mining su questa pagina."""
        if risposta.headers.get("tdm-reservation", "").strip() == "1":
            return True
        if META_TDM.search(risposta.content[:200_000]):
            return True
        url = str(risposta.url)
        p = urlsplit(url)
        radice = f"{p.scheme}://{p.netloc}"
        if radice not in self._tdmrep:
            self._tdmrep[radice] = []
            try:
                r = self._get(radice + "/.well-known/tdmrep.json")
                if r.status_code == 200 and isinstance(regole := r.json(), list):
                    self._tdmrep[radice] = [x for x in regole if isinstance(x, dict)]
            except (httpx.HTTPError, ValueError):
                pass
        for regola in self._tdmrep[radice]:
            if fnmatch.fnmatch(p.path or "/", str(regola.get("location", ""))):
                return str(regola.get("tdm-reservation")) == "1"
        return False
