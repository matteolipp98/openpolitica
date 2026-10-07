"""Client a mano (#71): le risposte le scrive Claude in sessione, con la stessa interfaccia di Gemini."""

import json

import pytest

from op_workers.catalogo.gemini import QuotaEsaurita
from op_workers.catalogo.manuale import ClientManuale, RispostaMancante, client


def test_senza_risposta_scrive_il_prompt_e_poi_legge_la_risposta(tmp_path):
    c = ClientManuale(tmp_path)
    with pytest.raises(RispostaMancante):
        c.json("Dimmi sì", {"type": "OBJECT"})
    (chiave,) = c.mancanti
    assert "Dimmi sì" in (tmp_path / f"{chiave}.prompt.md").read_text()
    (tmp_path / f"{chiave}.risposta.json").write_text(json.dumps({"ok": True}))
    r = c.json("Dimmi sì", {"type": "OBJECT"})
    assert (r.dati, r.modello, r.fornitore, r.famiglia) == ({"ok": True}, "claude-opus-5-5", "anthropic", "claude")


def test_risposta_mancante_e_una_quota_esaurita():
    """Chi gestisce solo QuotaEsaurita si ferma senza errore anche con il client a mano."""
    assert issubclass(RispostaMancante, QuotaEsaurita)


def test_scelta_del_client(monkeypatch, tmp_path):
    monkeypatch.setenv("OP_CLIENT", "manuale")
    monkeypatch.setenv("OP_MANUALE_DIR", str(tmp_path))
    assert isinstance(client(5), ClientManuale)
    monkeypatch.delenv("OP_CLIENT")
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    assert client(5).famiglia == "gemini"
