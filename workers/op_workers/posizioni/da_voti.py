"""Posizioni dei soggetti sugli enunciati, calcolate dai voti (ADR 0008, 0023; piano §3.6).

Regole a soglie, mai curve continue (ADR 0023), e mai stime: senza evidenza la posizione è
"non documentata". Cambiare queste regole richiede di cambiare CALCOLO_VERSIONE.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

Orientamento = Literal[-1, 0, 1]
Stato = Literal["documentata", "non_documentata", "divergente"]
Confidenza = Literal["piena", "ridotta"]

CALCOLO_VERSIONE = "pos-voti-1"


@dataclass(frozen=True)
class Parametri:
    quota_maggioranza: Decimal  # content/parametri.yaml: posizioni.quotaMaggioranzaGruppo
    membri_minimi: int  # posizioni.membriMinimi
    legislatura_riferimento: int  # posizioni.legislaturaRiferimento

    @classmethod
    def da_contenuti(cls, parametri: dict) -> Parametri:
        p = parametri["posizioni"]
        return cls(Decimal(str(p["quotaMaggioranzaGruppo"])), int(p["membriMinimi"]), int(p["legislaturaRiferimento"]))


@dataclass(frozen=True)
class Evidenza:
    votazione_id: str
    data: str  # ISO, AAAA-MM-GG
    legislatura: int
    orientamento: Orientamento  # già moltiplicato per la direzione dell'ancoraggio


@dataclass(frozen=True)
class Posizione:
    valore: int | None
    stato: Stato
    confidenza: Confidenza | None
    evidenze: tuple[Evidenza, ...]
    valido_dal: str | None
    calcolo_versione: str = CALCOLO_VERSIONE


def orientamento_persona(espressione: str) -> Orientamento | None:
    """Solo favorevole, contrario e astenuto sono evidenza; assenze e missioni no."""
    return {"favorevole": 1, "contrario": -1, "astenuto": 0}.get(espressione)  # type: ignore[return-value]


def orientamento_gruppo(espressioni: Iterable[str], p: Parametri) -> Orientamento | None:
    """Orientamento di un partito su una votazione, dai voti dei suoi membri alla data.

    q = (favorevoli - contrari) / (favorevoli + contrari + astenuti); oltre la quota di maggioranza
    il partito è a favore o contro, altrimenti è diviso (0). Sotto i membri minimi: nessuna evidenza.
    """
    lista = list(espressioni)
    fav, con, ast = lista.count("favorevole"), lista.count("contrario"), lista.count("astenuto")
    votanti = fav + con + ast
    if votanti < p.membri_minimi:
        return None
    q = Decimal(fav - con) / Decimal(votanti)
    if q >= p.quota_maggioranza:
        return 1
    if q <= -p.quota_maggioranza:
        return -1
    return 0


def arrotonda(x: Decimal) -> int:
    """Arrotonda lontano da zero sui mezzi (0,5 → 1; -0,5 → -1): simmetrico per costruzione."""
    segno = 1 if x >= 0 else -1
    return segno * int(abs(x).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def posizione(evidenze: Iterable[Evidenza], p: Parametri) -> Posizione:
    """Posizione su un enunciato dalle evidenze di voto (ADR 0023).

    - Si usa la legislatura di riferimento: valore = arrotonda(2 × media degli orientamenti).
    - Se ci sono voti a favore e contro, lo stato è "divergente": si mostrano entrambi, non si appiana.
    - Senza voti nella legislatura di riferimento si usa il più recente precedente, con confidenza ridotta.
    - Senza alcun voto: non documentata.
    """
    tutte = sorted(evidenze, key=lambda e: (e.data, e.votazione_id))
    correnti = tuple(e for e in tutte if e.legislatura == p.legislatura_riferimento)
    if correnti:
        media = Decimal(sum(e.orientamento for e in correnti)) / Decimal(len(correnti))
        valore = max(-2, min(2, arrotonda(2 * media)))
        stato: Stato = "divergente" if {1, -1} <= {e.orientamento for e in correnti} else "documentata"
        return Posizione(valore, stato, "piena", correnti, correnti[-1].data)
    precedenti = [e for e in tutte if e.legislatura < p.legislatura_riferimento]
    if precedenti:
        ultima = precedenti[-1]
        return Posizione(2 * ultima.orientamento, "documentata", "ridotta", (ultima,), ultima.data)
    return Posizione(None, "non_documentata", None, (), None)
