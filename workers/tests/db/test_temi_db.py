"""Tema delle promesse nel database (#75): un lotto finito non si richiede, scarti richiesti dopo, append-only."""

import json
from datetime import date

import httpx
import pytest
from psycopg.errors import CheckViolation, RaiseException

from op_workers.catalogo.gemini import Gemini
from op_workers.catalogo.manuale import ClientManuale
from op_workers.programmi import promesse as pr
from op_workers.programmi import temi as te
from op_workers.programmi.scarica import Pagina, collega, salva_documento

TESTO = "Introdurremo il salario minimo a 9 euro l'ora entro il 2023.\n\nAboliremo il superbollo sulle auto."
PROMESSE = [
    {"citazione": "Introdurremo il salario minimo a 9 euro l'ora", "misura": "Salario minimo di 9 euro l'ora"},
    {"citazione": "Aboliremo il superbollo sulle auto", "misura": "Niente superbollo"},
]


def gemini_finto(risposte: list, chiamate: list) -> Gemini:
    """Gemini con trasporto finto: restituisce in ordine le risposte date."""

    def gestore(req):
        chiamate.append(req)
        testo = json.dumps(risposte[len(chiamate) - 1])
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": testo}]}}],
                                         "modelVersion": "finto-001"})  # fmt: skip

    return Gemini(chiave="k", modello="finto", client=httpx.Client(transport=httpx.MockTransport(gestore)), pausa=0)


def _con_promesse(conn):
    """Un programma comune ad Azione e Italia Viva con due promesse: salario minimo e superbollo."""
    for s in ("azione", "italia-viva"):
        conn.execute("insert into core.partito (slug, nome) values (%s, %s)", (s, s))
    salva_documento(conn, url="https://example.org/p.pdf", data=date(2022, 9, 25), sha256="c" * 64,
                    lette=[Pagina(1, TESTO, False)])  # fmt: skip
    collega(conn, partiti=["azione", "italia-viva"], elezione=date(2022, 9, 25), sha256="c" * 64)
    pr.esegui(conn, gemini_finto([PROMESSE], []))


def test_classifica_salva_e_non_richiede(conn):
    _con_promesse(conn)
    chiamate = []
    conteggi, fermo = te.esegui(conn, gemini_finto([[{"n": 1, "tema": "economia"}, {"n": 2, "tema": "bollo"}]],
                                                   chiamate))  # fmt: skip
    assert not fermo and len(chiamate) == 1
    c = conteggi[0]
    assert (c.partiti, c.lotti, c.nuovi, c.classificate, c.scartate) == ("azione, italia-viva", 1, 1, 1, 1)
    assert conn.execute(
        """select p.misura, t.tema, l.modello_id, l.prompt_versione, r.stadio, r.modello_id
           from core.promessa_tema_attuale t join core.promessa p on p.id = t.promessa_id
           join core.promessa_tema_lotto l on l.id = t.lotto_id join core.run_modello r on r.id = l.run_modello_id"""
    ).fetchall() == [("Salario minimo di 9 euro l'ora", "economia", "finto", "promesse/tema.v1", "programmi.temi",
                      "finto-001")]  # fmt: skip

    # al giro dopo si richiede solo la promessa scartata, con un altro modello (aggiornamenti con Gemini)
    altro = gemini_finto([None, [{"n": 1, "tema": "ambiente"}]], chiamate)  # la prima risposta è già usata
    altro.modello = "altro"
    conteggi, _ = te.esegui(conn, altro)
    assert len(chiamate) == 2 and "[2]" not in json.loads(chiamate[1].content)["contents"][0]["parts"][0]["text"]
    assert te.per_partito(conn) == [("azione", "ambiente", 1), ("azione", "economia", 1),
                                    ("italia-viva", "ambiente", 1), ("italia-viva", "economia", 1)]  # fmt: skip

    # tutto classificato: nessuna chiamata
    conteggi, _ = te.esegui(conn, gemini_finto([], chiamate))
    assert len(chiamate) == 2 and conteggi[0].gia_fatti == 1

    with pytest.raises(RaiseException, match="append-only"):
        conn.execute("update core.promessa_tema set tema = 'altro'")


def test_client_a_mano(conn, tmp_path):
    _con_promesse(conn)
    manuale = ClientManuale(tmp_path)
    conteggi, fermo = te.esegui(conn, manuale)
    assert not fermo and conteggi[0].mancanti == 1
    (chiave,) = manuale.mancanti
    assert "promesse" in (tmp_path / f"{chiave}.prompt.md").read_text(encoding="utf8")
    (tmp_path / f"{chiave}.risposta.json").write_text(json.dumps([{"n": 1, "tema": "economia"},
                                                                  {"n": 2, "tema": "altro"}]))  # fmt: skip
    conteggi, _ = te.esegui(conn, ClientManuale(tmp_path))
    assert conteggi[0].classificate == 2
    assert conn.execute(
        "select distinct r.modello_id, m.famiglia from core.run_modello r join core.modello m on m.id = r.modello_id "
        "where r.stadio = 'programmi.temi'"
    ).fetchall() == [("claude-opus-5-5", "claude")]


def test_tema_sconosciuto_rifiutato_dal_database(conn):
    _con_promesse(conn)
    te.esegui(conn, gemini_finto([[{"n": 1, "tema": "economia"}]], []))
    with pytest.raises(CheckViolation):
        conn.execute("insert into core.promessa_tema (promessa_id, lotto_id, tema) "
                     "select promessa_id, lotto_id, 'cultura' from core.promessa_tema")  # fmt: skip
