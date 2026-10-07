"""Programmi nel database (#36): idempotenza, liste comuni, append-only, rilettura (#63)."""

import hashlib
from datetime import date

import httpx
import pytest
from psycopg.errors import RaiseException, UniqueViolation

from op_workers.programmi import promesse as pr
from op_workers.programmi import scarica as sc
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


# ---------- Rilettura quando cambia l'estrazione (#63) ----------

ELENCO = "https://example.org/elezioni/elenco.json"
PDF = b"%PDF-1.4 programma di prova"
SHA_PDF = hashlib.sha256(PDF).hexdigest()


def _cartella(tmp_path):
    (tmp_path / "programmi.yaml").write_text(
        f"elezioni:\n  - data: 2022-09-25\n    elenco: {ELENCO}\n"
        "    programmi:\n      - {contrassegno: 1, partiti: [azione]}\n",
        encoding="utf8",
    )
    return tmp_path


def _http():
    elenco = {"contrass": [{"n_ord": 1, "e_file": [{"tp_doc": 2, "f_doc": "p.pdf"}]}]}
    return httpx.Client(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json=elenco) if str(r.url) == ELENCO else httpx.Response(200, content=PDF)
        )
    )


def test_rilegge_il_documento_letto_con_una_versione_vecchia(conn, tmp_path, monkeypatch):
    _partiti(conn, "azione")
    vecchia = [Pagina(1, "Testo letto male.", False)]
    salva_documento(conn, url="https://example.org/p.pdf", data=EL, sha256=SHA_PDF, lette=vecchia, estrazione=1)
    collega(conn, partiti=["azione"], elezione=EL, sha256=SHA_PDF)
    letture = []
    monkeypatch.setattr(sc, "pagine", lambda pdf: letture.append(pdf) or [Pagina(1, "Testo riletto.", True)])

    [riga] = sc.esegui(conn, _http(), _cartella(tmp_path))
    assert riga.endswith(f"| 1 | 1 | 1 | riletto (1 → {sc.ESTRAZIONE}) |") and len(letture) == 1
    # niente si cancella: due letture dello stesso documento, vale la più recente
    assert conn.execute("select estrazione from core.documento order by estrazione").fetchall() == [
        (1,),
        (sc.ESTRAZIONE,),
    ]
    assert conn.execute(
        """select d.estrazione, p.testo, p.ocr from core.documento_attuale d
           join core.documento_paragrafo p on p.documento_id = d.id"""
    ).fetchall() == [(sc.ESTRAZIONE, "Testo riletto.", True)]
    assert conn.execute("select count(*) from core.programma").fetchone()[0] == 2
    [(doc_id, _)] = pr.documenti(conn)
    assert doc_id == conn.execute("select id from core.documento_attuale").fetchone()[0]

    # già letto con la versione attuale: non si rilegge
    [riga] = sc.esegui(conn, _http(), _cartella(tmp_path))
    assert riga.endswith("| già letto |") and len(letture) == 1
    assert conn.execute("select count(*) from core.documento").fetchone()[0] == 2


def test_stessa_impronta_e_stessa_versione_non_si_ripetono(conn):
    salva_documento(conn, url="https://example.org/p.pdf", data=EL, sha256=SHA, lette=[Pagina(1, "Testo.", False)])
    with pytest.raises(UniqueViolation):
        salva_documento(conn, url="https://example.org/p.pdf", data=EL, sha256=SHA, lette=[Pagina(1, "Testo.", False)])
