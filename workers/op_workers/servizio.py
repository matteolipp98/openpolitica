"""Servizio dei worker su Render (ADR 0017): risponde ai controlli di salute.

L'import dei voti parte da un solo posto, il workflow `Database` di GitHub Actions (ogni 6 ore, con il
rilascio del sito a valle): due import insieme sprecano le richieste ai server di Camera e Senato (#30).
Qui l'import notturno resta disponibile solo se si imposta IMPORT_NOTTURNO=1.

Il sito non dipende da questo servizio: legge pagine statiche (ADR 0021, 0029). Se il servizio è giù,
il sito resta in piedi; i voti nuovi arrivano al giro successivo.

Endpoint:
  GET /         breve descrizione
  GET /salute   stato in JSON: versione, database raggiungibile, fin dove arrivano i voti per ramo

Uso: python -m op_workers.servizio  (PORT, DATABASE_URL facoltativo, IMPORT_NOTTURNO=0, ORA_IMPORT=3)
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

log = logging.getLogger("op_workers.servizio")

STATO: dict[str, object] = {
    "avviato_il": datetime.now(UTC).isoformat(timespec="seconds"),
    "versione": os.environ.get("RENDER_GIT_COMMIT", "sviluppo")[:12],
    "ultimo_import": None,
    "esito_ultimo_import": None,
}


def stato_database() -> tuple[bool | None, dict[str, str]]:
    """(database raggiungibile, data dell'ultima votazione importata per ramo)."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        return None, {}
    try:
        import psycopg

        with psycopg.connect(url, connect_timeout=5) as c:
            righe = c.execute("select ramo, max(data) from core.votazione group by ramo").fetchall()
        return True, {r: d.isoformat() for r, d in righe}
    except Exception:  # noqa: BLE001 - lo stato si riporta, non si solleva
        log.exception("database non raggiungibile")
        return False, {}


def import_notturno_attivo() -> bool:
    return bool(os.environ.get("DATABASE_URL")) and os.environ.get("IMPORT_NOTTURNO", "0") == "1"


class Gestore(BaseHTTPRequestHandler):
    def _json(self, codice: int, corpo: dict) -> None:
        dati = json.dumps(corpo, ensure_ascii=False).encode()
        self.send_response(codice)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(dati)))
        self.end_headers()
        self.wfile.write(dati)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/salute":
            db, ultime = stato_database()
            self._json(200 if db is not False else 503, {**STATO, "database": db, "ultime_votazioni": ultime})
        elif self.path == "/":
            self._json(200, {"servizio": "openpolitica worker", "salute": "/salute"})
        else:
            self._json(404, {"errore": "non trovato"})

    def do_HEAD(self) -> None:  # noqa: N802 - Render controlla il servizio anche con HEAD
        self.send_response(200 if self.path in ("/", "/salute") else 404)
        self.end_headers()

    def log_message(self, fmt: str, *args: object) -> None:
        log.info("%s %s", self.address_string(), fmt % args)


def importa_tutto() -> None:
    import psycopg

    from op_workers.anagrafica.sincronizza import sincronizza
    from op_workers.connettori.camera import ConnettoreCamera
    from op_workers.connettori.importa_voti import importa
    from op_workers.connettori.senato import ConnettoreSenato

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        sincronizza(conn)
        conn.commit()
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
        esiti = {c.ramo: importa(conn, c, 19) for c in (ConnettoreCamera(), ConnettoreSenato())}
    STATO["esito_ultimo_import"] = {r: vars(e) for r, e in esiti.items()}


def ciclo_import(ora: int) -> None:
    """Un import al giorno all'ora indicata (UTC). Un errore non ferma il servizio: si riprova il giorno dopo."""
    while True:
        adesso = datetime.now(UTC)
        prossimo = adesso.replace(hour=ora, minute=0, second=0, microsecond=0)
        if prossimo <= adesso:
            prossimo += timedelta(days=1)
        time.sleep((prossimo - adesso).total_seconds())
        try:
            importa_tutto()
        except Exception as e:  # noqa: BLE001
            log.exception("import fallito")
            STATO["esito_ultimo_import"] = f"errore: {type(e).__name__}: {e}"
        STATO["ultimo_import"] = datetime.now(UTC).isoformat(timespec="seconds")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    if import_notturno_attivo():
        threading.Thread(target=ciclo_import, args=(int(os.environ.get("ORA_IMPORT", "3")),), daemon=True).start()
    else:
        log.info("import notturno spento: lo fa il workflow Database di GitHub Actions")
    porta = int(os.environ.get("PORT", "10000"))
    log.info("in ascolto sulla porta %s", porta)
    ThreadingHTTPServer(("0.0.0.0", porta), Gestore).serve_forever()  # noqa: S104 - richiesto da Render
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
