"""Client minimo della API di Gemini (ADR 0038): output JSON con schema, tetto di chiamate, quota giornaliera.

La chiave sta in GEMINI_API_KEY (secret dell'environment dev). Il modello è un nome con versione,
registrato in ogni run (ADR 0016).
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass

import httpx

API = "https://generativelanguage.googleapis.com/v1beta"
MODELLO_PREDEFINITO = "gemini-3.5-flash"  # versione 3.5-flash-05-2026; 2.5-flash non è più disponibile (#64)


class QuotaEsaurita(RuntimeError):
    """Finite le chiamate (tetto dell'esecuzione o quota giornaliera): si riprende al giro successivo."""


class ErroreGemini(RuntimeError):
    pass


@dataclass
class Risposta:
    dati: object
    token_in: int
    token_out: int
    latenza_ms: int
    modello: str


class Gemini:
    def __init__(
        self,
        chiave: str | None = None,
        modello: str | None = None,
        max_chiamate: int = 20,
        pausa: float = 7.0,
        client: httpx.Client | None = None,
        attesa_errori: float = 10.0,
    ) -> None:
        self.chiave = chiave or os.environ.get("GEMINI_API_KEY", "")
        if not self.chiave:
            raise ErroreGemini("manca GEMINI_API_KEY")
        self.modello = modello or os.environ.get("GEMINI_MODELLO") or MODELLO_PREDEFINITO
        self.max_chiamate = max_chiamate
        self.chiamate = 0
        self.pausa = pausa  # i piani gratuiti limitano anche le chiamate al minuto
        self.http = client or httpx.Client(timeout=300)
        self.attesa_errori = attesa_errori  # secondi in più a ogni nuovo tentativo dopo un 5xx o un errore di rete
        self._ultima = 0.0

    def modelli(self) -> list[str]:
        r = self.http.get(f"{API}/models", headers={"x-goog-api-key": self.chiave})
        r.raise_for_status()
        return [m["name"].removeprefix("models/") for m in r.json().get("models", [])]

    def json(self, prompt: str, schema: dict) -> Risposta:
        if self.chiamate >= self.max_chiamate:
            raise QuotaEsaurita(f"tetto di {self.max_chiamate} chiamate per esecuzione raggiunto")
        corpo = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json", "responseSchema": schema},
        }
        for tentativo in range(4):
            attesa = self.pausa - (time.monotonic() - self._ultima)
            if attesa > 0:
                time.sleep(attesa)
            inizio = time.monotonic()
            try:
                r = self.http.post(
                    f"{API}/models/{self.modello}:generateContent",
                    headers={"x-goog-api-key": self.chiave, "Content-Type": "application/json"},
                    json=corpo,
                )
            except httpx.TransportError:  # timeout o rete: come un 5xx, si riprova (#69)
                self._ultima = time.monotonic()
                time.sleep(self.attesa_errori * (tentativo + 1))
                continue
            self._ultima = time.monotonic()
            if r.status_code == 429:
                testo = r.text
                if re.search(r"PerDay|per day|daily", testo, re.IGNORECASE):
                    raise QuotaEsaurita("quota giornaliera di Gemini esaurita")
                m = re.search(r'"retryDelay":\s*"(\d+)s"', testo)
                time.sleep(int(m.group(1)) + 1 if m else 30 * (tentativo + 1))
                continue
            if r.status_code >= 500:
                time.sleep(self.attesa_errori * (tentativo + 1))
                continue
            if r.status_code != 200:
                raise ErroreGemini(f"HTTP {r.status_code}: {r.text[:300]}")
            self.chiamate += 1
            d = r.json()
            try:
                testo = d["candidates"][0]["content"]["parts"][0]["text"]
                dati = json.loads(testo)
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                raise ErroreGemini(f"risposta non valida: {str(d)[:300]}") from e
            uso = d.get("usageMetadata", {})
            return Risposta(
                dati,
                uso.get("promptTokenCount", 0),
                uso.get("candidatesTokenCount", 0),
                int((self._ultima - inizio) * 1000),
                d.get("modelVersion", self.modello),
            )
        raise QuotaEsaurita("Gemini continua a rifiutare le richieste (429, 5xx o rete): si riprova al prossimo giro")
