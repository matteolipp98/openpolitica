"""Client "a mano" (#71): stessa interfaccia di Gemini, ma le risposte le scrive Claude in una sessione di lavoro.

Serve per l'inizializzazione di catalogo e promesse senza la quota di Gemini (decisione dell'utente, 8 ottobre);
gli aggiornamenti tornano a Gemini. Per ogni prompt senza risposta il client scrive nella cartella di lavoro
<impronta>.prompt.md (con lo schema) e solleva RispostaMancante: la pipeline salta il lotto e continua.
La risposta va in <impronta>.risposta.json; al giro dopo il client la legge e la restituisce come farebbe Gemini.
Il modello registrato con ogni risposta è quello che l'ha scritta (claude-opus-5-5, famiglia claude).

Uso: OP_CLIENT=manuale OP_MANUALE_DIR=<cartella> python -m op_workers.catalogo.genera ...
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from op_workers.catalogo.gemini import Gemini, QuotaEsaurita, Risposta

MODELLO = "claude-opus-5-5"


class RispostaMancante(QuotaEsaurita):
    """Il prompt aspetta una risposta scritta a mano: la pipeline salta il lotto e prosegue."""


class ClientManuale:
    fornitore = "anthropic"
    famiglia = "claude"

    def __init__(self, cartella: Path, modello: str = MODELLO) -> None:
        self.cartella = cartella
        self.modello = modello
        self.chiamate = 0
        self.mancanti: list[str] = []
        cartella.mkdir(parents=True, exist_ok=True)

    def json(self, prompt: str, schema: dict) -> Risposta:
        chiave = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        risposta = self.cartella / f"{chiave}.risposta.json"
        if risposta.exists():
            self.chiamate += 1
            dati = json.loads(risposta.read_text(encoding="utf8"))
            return Risposta(dati, 0, 0, 0, self.modello, self.fornitore, self.famiglia)
        testo = f"{prompt}\n\n---\nRispondi solo con JSON valido secondo questo schema:\n\n"
        testo += json.dumps(schema, ensure_ascii=False, indent=1)
        (self.cartella / f"{chiave}.prompt.md").write_text(testo + "\n", encoding="utf8")
        self.mancanti.append(chiave)
        raise RispostaMancante(f"risposta da scrivere: {chiave}.risposta.json")


def client(max_chiamate: int) -> Gemini | ClientManuale:
    """Gemini, oppure il client a mano se OP_CLIENT=manuale (cartella in OP_MANUALE_DIR)."""
    if os.environ.get("OP_CLIENT") == "manuale":
        return ClientManuale(Path(os.environ["OP_MANUALE_DIR"]))
    return Gemini(max_chiamate=max_chiamate)
