"""Programmi nel database (#36): idempotenza, liste comuni, append-only."""

from datetime import date

import pytest
from psycopg.errors import RaiseException

from op_workers.programmi.scarica import Pagina, collega, salva_documento

SHA = "a" * 64
EL = date(2022, 9, 25)


def _partiti(c, *slug):
    for s in slug:
        c.execute("insert into core.partito (slug, nome) values (%s, %s)", (s, s))


def test_documento_paragrafi_e_lista_comune(conn):
    _partiti(conn, "azione", "italia-viva")
    lette = [Pagina(1, "Primo paragrafo.\n\nSecondo paragrafo.", False), Pagina(2, "Letto con l'OCR.", True)]
    assert salva_documento(conn, url="https://example.org/p.pdf", data=EL, sha256=SHA, lette=lette) == 3
    assert collega(conn, partiti=["azione", "italia-viva"], elezione=EL, sha256=SHA) == 2
    assert collega(conn, partiti=["azione", "italia-viva"], elezione=EL, sha256=SHA) == 0
    assert conn.execute("select pagine, pagine_ocr from core.documento").fetchone() == (2, 1)
    assert conn.execute("select n, pagina, ocr from core.documento_paragrafo order by n").fetchall() == [
        (1, 1, False),
        (2, 1, False),
        (3, 2, True),
    ]


def test_documento_append_only(conn):
    salva_documento(conn, url="https://example.org/p.pdf", data=EL, sha256=SHA, lette=[Pagina(1, "Testo.", False)])
    with pytest.raises(RaiseException, match="append-only"):
        conn.execute("update core.documento_paragrafo set testo = 'altro'")
