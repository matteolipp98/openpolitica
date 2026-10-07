"""Forma comune dei dati che i connettori di Camera e Senato restituiscono (ADR 0002)."""

from __future__ import annotations

import html
import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal, Protocol

Ramo = Literal["camera", "senato"]
Espressione = Literal[
    "favorevole", "contrario", "astenuto", "non_votante", "assente", "in_missione", "presidente", "votante_segreto"
]


class DatoInatteso(ValueError):
    """La fonte ha restituito un valore che non sappiamo interpretare: meglio fermarsi che importare male."""


@dataclass(frozen=True)
class VotazioneGrezza:
    ramo: Ramo
    legislatura: int
    id_esterno: str
    data: date
    tipo: str | None
    titolo: str | None
    descrizione: str | None
    atto_ref: str | None
    atto_titolo: str | None
    finale: bool
    fiducia: bool
    segreta: bool
    favorevoli: int
    contrari: int
    astenuti: int
    approvata: bool | None
    url: str


@dataclass(frozen=True)
class VotoGrezzo:
    id_votazione_esterno: str
    id_persona_esterno: str
    espressione: Espressione
    id_gruppo_esterno: str | None


@dataclass(frozen=True)
class ConteggioGrezzo:
    """Quanti voti di un tipo ha dato un gruppo in una votazione, contati dal server della fonte."""

    id_votazione_esterno: str
    id_gruppo_esterno: str | None
    espressione: Espressione
    n: int


@dataclass(frozen=True)
class ParlamentareGrezzo:
    ramo: Ramo
    id_esterno: str
    nome: str
    cognome: str


@dataclass(frozen=True)
class AdesioneGrezza:
    ramo: Ramo
    id_persona_esterno: str
    id_gruppo_esterno: str
    dal: date
    al: date | None


class ConnettoreVoti(Protocol):
    ramo: Ramo

    def votazioni(self, legislatura: int, dal: date) -> Iterator[VotazioneGrezza]: ...
    def voti_del_giorno(self, legislatura: int, giorno: date) -> Iterator[VotoGrezzo]: ...
    def parlamentari(self, legislatura: int) -> Iterator[ParlamentareGrezzo]: ...
    def adesioni(self, legislatura: int) -> Iterator[AdesioneGrezza]: ...


class ConnettoreConteggi(ConnettoreVoti, Protocol):
    """Fonte che sa contare da sola: si scaricano i conteggi per gruppo e solo i voti individuali che servono."""

    def conteggi_del_giorno(self, legislatura: int, giorno: date) -> Iterator[ConteggioGrezzo]: ...
    def voti_scelti_del_giorno(
        self, legislatura: int, giorno: date, persone: set[str], gruppi: set[str]
    ) -> Iterator[VotoGrezzo]: ...


def finestre_mensili(dal: date, al: date | None = None) -> list[tuple[date, date]]:
    """Intervalli di un mese da `dal` a `al` (oggi se assente), estremi inclusi.

    Le query su un'intera legislatura vanno in errore (HTTP 500) sui server di Camera e Senato:
    si chiede un mese alla volta.
    """
    al = al or date.today()
    out = []
    inizio = dal
    while inizio <= al:
        prossimo = date(inizio.year + inizio.month // 12, inizio.month % 12 + 1, 1)
        out.append((inizio, min(prossimo - timedelta(days=1), al)))
        inizio = prossimo
    return out


def pulisci_titolo(testo: str | None) -> str | None:
    """Titolo di una legge leggibile (#73). La Camera lo dà con il tipo RDF in coda
    (^^http://www.w3.org/2001/XMLSchema#string), entità HTML (&quot;, &egrave;) e tag (<em>)."""
    if testo is None:
        return None
    t = re.sub(r"\^\^<?https?://\S+$", "", testo.strip())
    t = html.unescape(html.unescape(t))  # alcuni titoli sono codificati due volte (&amp;quot;)
    t = re.sub(r"<[^>]+>", "", t).replace("\xa0", " ").replace('\\"', '"')
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def chiave_atto(titolo: str) -> str:
    """La stessa legge votata nei due rami ha titoli quasi uguali: senza numero dell'atto, note tra parentesi
    in coda, virgolette e punteggiatura (ADR 0030: mai due domande dallo stesso atto)."""
    t = pulisci_titolo(titolo) or ""
    if dl := re.search(r"decreto-legge (\d{1,2}°? \w+ \d{4}), n\. ?(\d+)", t):  # conversione: conta il decreto
        return f"decreto-legge {dl.group(1).replace('°', '')} n {dl.group(2)}".lower()
    t = re.sub(r"^S\. ?\d+\. ?- ?", "", t)  # "S. 899. - " davanti ai disegni di legge arrivati dal Senato
    t = re.sub(r"(\s*\([^()]*\))+\s*$", "", t)  # "(approvato dal Senato) (1551)" in coda
    return re.sub(r"\W+", " ", t.lower()).strip()[:160]
