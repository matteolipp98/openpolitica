import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

from op_workers import servizio


def test_salute_senza_database(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), servizio.Gestore)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{srv.server_port}/salute", timeout=5) as r:
            corpo = json.loads(r.read())
        assert r.status == 200
        assert corpo["database"] is None
        assert "versione" in corpo
    finally:
        srv.shutdown()


def test_head_risponde(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), servizio.Gestore)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{srv.server_port}/", method="HEAD")
        with urllib.request.urlopen(req, timeout=5) as r:
            assert r.status == 200
    finally:
        srv.shutdown()
