"""Forma comune dei dati che i connettori di Camera e Senato restituiscono (ADR 0002)."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from typing import Literal, Protocol

Ramo = Literal["camera", "senato"]
Espressione = Literal["favorevole", "contrario", "astenuto", "non_votante", "assente", "in_missione", "presidente"]


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
