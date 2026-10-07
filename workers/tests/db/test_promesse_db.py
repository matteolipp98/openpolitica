"""Promesse nel database (#37): un lotto già fatto non si richiede, scarti contati, append-only."""

import json
from datetime import date

import httpx
import pytest
from psycopg.errors import RaiseException

from op_workers.catalogo.gemini import Gemini
from op_workers.programmi import promesse as pr
from op_workers.programmi.scarica import Pagina, collega, salva_documento

SHA = "b" * 64
TESTO = (
    "Introdurremo il salario minimo a 9 euro l'ora entro il 2023.\n\n"
    "Aboliremo il superbollo sulle auto.\n\n"
    "Il paese ha bisogno di fiducia."
)


def gemini_finto(risposte: list, chiamate: list, **kw) -> Gemini:
    """Gemini con trasporto finto: restituisce in ordine le risposte date."""

    def gestore(req):
        chiamate.append(req)
        testo = json.dumps(risposte[len(chiamate) - 1])
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": testo}]}}],
                                         "modelVersion": "finto-001"})  # fmt: skip

    return Gemini(chiave="k", modello="finto", client=httpx.Client(transport=httpx.MockTransport(gestore)), pausa=0,
                  **kw)  # fmt: skip


def _programma(conn):
    for s in ("azione", "italia-viva"):
        conn.execute("insert into core.partito (slug, nome) values (%s, %s)", (s, s))
    salva_documento(conn, url="https://example.org/p.pdf", data=date(2022, 9, 25), sha256=SHA,
                    lette=[Pagina(1, TESTO, False)])  # fmt: skip
    collega(conn, partiti=["azione", "italia-viva"], elezione=date(2022, 9, 25), sha256=SHA)


RISPOSTA = [
    {"citazione": "Introdurremo il salario minimo a 9 euro l’ora", "misura": "Salario minimo di 9 euro l'ora",
     "orizzonte": "entro il 2023", "livello_competenza": "nazionale"},
    {"citazione": "Aboliremo il superbollo sulle auto", "misura": "Niente superbollo",
     "livello_competenza": "non_chiaro"},
    {"citazione": "Aboliremo il bollo auto per tutti", "misura": "Niente bollo"},
]  # fmt: skip


def test_estrae_salva_e_non_richiede_lo_stesso_lotto(conn):
    _programma(conn)
    chiamate = []
    g = gemini_finto([RISPOSTA], chiamate)
    conteggi, fermo = pr.esegui(conn, g)
    assert not fermo and len(chiamate) == 1
    c = conteggi[0]
    assert (c.partiti, c.lotti, c.nuovi, c.estratte, c.scartate) == ("azione, italia-viva", 1, 1, 2, 1)
    assert conn.execute(
        "select paragrafo_da, misura, orizzonte, livello_competenza, stato_revisione from core.promessa order by 1"
    ).fetchall() == [
        (1, "Salario minimo di 9 euro l'ora", "entro il 2023", "nazionale", "non_rivista"),
        (2, "Niente superbollo", None, None, "non_rivista"),
    ]  # fmt: skip
    assert conn.execute(
        """select l.paragrafo_da, l.paragrafo_a, l.modello_id, l.prompt_versione, l.estratte, l.scartate, r.modello_id
           from core.promessa_lotto l join core.run_modello r on r.id = l.run_modello_id"""
    ).fetchall() == [(1, 3, "finto", "promesse/estrai.v1", 2, 1, "finto-001")]

    # seconda esecuzione: stesso modello e stesso prompt, nessuna chiamata
    conteggi, _ = pr.esegui(conn, gemini_finto([], chiamate))
    assert len(chiamate) == 1 and (conteggi[0].gia_fatti, conteggi[0].nuovi) == (1, 0)
    assert conn.execute("select count(*) from core.promessa").fetchone()[0] == 2

    # un modello diverso rifà il lotto
    altro = gemini_finto([RISPOSTA, []], chiamate)
    altro.modello = "altro"
    pr.esegui(conn, altro)
    assert len(chiamate) == 2


def test_tetto_di_chiamate_ferma_senza_salvare_a_meta(conn):
    _programma(conn)
    conteggi, fermo = pr.esegui(conn, gemini_finto([], [], max_chiamate=0))
    assert fermo and conteggi[0].nuovi == 0
    assert conn.execute("select count(*) from core.promessa_lotto").fetchone()[0] == 0


def test_filtro_per_partito_e_append_only(conn):
    _programma(conn)
    assert pr.documenti(conn, "lega") == []
    assert len(pr.documenti(conn, "azione")) == 1
    pr.esegui(conn, gemini_finto([RISPOSTA], []), partito="italia-viva")
    with pytest.raises(RaiseException, match="append-only"):
        conn.execute("update core.promessa set misura = 'altro'")
