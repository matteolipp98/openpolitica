"""Pulizia del testo, segnali di contenuto ostile e filtro sui nomi del perimetro, senza modelli (ADR 0002, 0026)."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Iterable

# Caratteri a larghezza zero, controlli di direzione e trattini morbidi: invisibili a chi legge, ma non a un modello
INVISIBILI = re.compile("[­᠎​-‏‪-‮⁠-⁤⁦-⁩﻿]")

# Frasi tipiche di chi prova a dare istruzioni a un modello (ADR 0026). Non si scarta il documento: si segna.
INIEZIONE = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"ignora\s+(tutte\s+)?(le\s+)?istruzioni",
        r"ignore\s+(all\s+)?(the\s+)?(previous|prior|above)\s+instructions",
        r"system\s+prompt",
        r"(sei|you\s+are)\s+(ora\s+|now\s+)?(un|an?)\s+(modello\s+linguistico|assistente|ai\b|language\s+model|assistant)",
        r"(classifica|valuta|considera)\s+quest[oa]\s+(dichiarazione|testo|documento)\s+come",
        r"<\|im_start\|>|\[/?INST\]|<<SYS>>",
    )
]


def pulisci(testo: str | None) -> str:
    """NFKC, niente caratteri invisibili o di controllo, spazi compattati; gli a capo restano."""
    if not testo:
        return ""
    t = INVISIBILI.sub("", unicodedata.normalize("NFKC", testo))
    t = "".join(c for c in t if c in "\n\t" or not unicodedata.category(c).startswith("C"))
    righe = [re.sub(r"[ \t]+", " ", r).strip() for r in t.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(righe)).strip()


def sospetto(testo: str) -> str | None:
    """Il motivo per cui il testo sembra rivolgersi a un modello invece che a chi legge, se c'è."""
    for p in INIEZIONE:
        if m := p.search(testo):
            return f"frase rivolta ai modelli: {m.group(0)[:80]!r}"
    return None


def impronta(*parti: str | None) -> str:
    return hashlib.sha256("\n".join(p or "" for p in parti).encode("utf8")).hexdigest()


class Perimetro:
    """Riconosce le persone del perimetro dalle forme dei loro nomi (content/alias/), con i confini di parola.

    `trova` usa solo le forme elencate: un cognome condiviso con altri (forme_escluse) non basta a dire di chi
    si parla (ADR 0027). `nomina` è più largo e decide solo se un articolo va tenuto: basta anche il cognome
    con l'iniziale maiuscola ("Meloni"), perché l'attribuzione vera si fa dopo (#42).
    """

    def __init__(self, forme: dict[str, Iterable[str]], cognomi: Iterable[str] = ()):
        self._re = {slug: _regola(fs) for slug, fs in forme.items() if fs}
        c = sorted(set(cognomi), key=len, reverse=True)
        self._cognomi = re.compile(rf"(?<!\w)({'|'.join(map(re.escape, c))})(?!\w)") if c else None

    def trova(self, *testi: str | None) -> list[str]:
        t = _apostrofi(pulisci(" \n".join(x or "" for x in testi)))
        return sorted(slug for slug, r in self._re.items() if r.search(t))

    def nomina(self, *testi: str | None) -> bool:
        if self.trova(*testi):
            return True
        return bool(self._cognomi and self._cognomi.search(_apostrofi(pulisci(" \n".join(x or "" for x in testi)))))


def _regola(forme: Iterable[str]) -> re.Pattern[str]:
    alternative = "|".join(re.escape(_apostrofi(f)) for f in sorted(forme, key=len, reverse=True))
    return re.compile(rf"(?<!\w)({alternative})(?!\w)", re.IGNORECASE)


def _apostrofi(t: str) -> str:
    return t.replace("’", "'").replace("‘", "'")
