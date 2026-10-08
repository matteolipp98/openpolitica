"""Documenti grezzi nel database (#41): filtro sul perimetro, doppioni, conservazione dei testi (ADR 0003)."""

from datetime import UTC, datetime, timedelta

import httpx
import pytest
from psycopg.errors import CheckViolation, RaiseException

from op_workers.notizie.raccogli import Fonte, cancella_scaduti, raccogli_fonte, registra
from op_workers.notizie.rete import Rete
from op_workers.notizie.testo import Perimetro

ADESSO = datetime(2026, 10, 8, 12, tzinfo=UTC)
PERIMETRO = Perimetro({"elly-schlein": ["Elly Schlein"], "giorgia-meloni": ["Giorgia Meloni"]}, ["Meloni", "Schlein"])
CORPO = "Nel suo intervento ha spiegato la proposta sul salario minimo e sulla sanità pubblica. " * 6

FEED = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
<item><title>Schlein: salario minimo subito</title><link>https://giornale.test/a1</link></item>
<item><title>Meteo: pioggia al nord</title><link>https://giornale.test/a2</link></item>
<item><title>Meloni risponde</title><link>https://riservato.test/a3</link></item>
</channel></rss>"""


def _pagina(titolo: str, testo: str) -> str:
    corpo = f"<article><h1>{titolo}</h1><p>{testo}</p></article>"
    return f"<html><head><title>{titolo}</title></head><body>{corpo}</body></html>"


def gestore(req: httpx.Request) -> httpx.Response:
    if req.url.path in ("/robots.txt", "/.well-known/tdmrep.json"):
        return httpx.Response(404)
    if str(req.url) == "https://giornale.test/feed":
        return httpx.Response(200, content=FEED)
    if str(req.url) == "https://giornale.test/a1":
        return httpx.Response(200, text=_pagina("Schlein: salario minimo subito", "Elly Schlein ha detto. " + CORPO))
    if str(req.url) == "https://riservato.test/a3":
        meta = '<meta name="tdm-reservation" content="1">'
        return httpx.Response(
            200, text=_pagina("Meloni risponde", "Giorgia Meloni. " + CORPO).replace("<head>", "<head>" + meta)
        )
    if str(req.url) == "https://partito.test/feed":
        return httpx.Response(
            200, content=FEED.replace(b"giornale.test", b"partito.test").replace(b"riservato.test", b"partito.test")
        )
    if req.url.host == "partito.test":
        return httpx.Response(200, text=_pagina("Comunicato", CORPO))
    return httpx.Response(404)


def _rete() -> Rete:
    return Rete(httpx.Client(transport=httpx.MockTransport(gestore)), pausa=0)


def _righe(conn, fonte):
    return conn.execute(
        """select url, livello, soggetti, testo is not null, testo_scade_il, tdm_riservato
           from core.documento_grezzo where fonte = %s order by url""",
        (fonte,),
    ).fetchall()


def test_giornale_solo_perimetro_testo_a_scadenza_e_tdm(conn):
    fonte = Fonte("giornale", "C", "rss", "https://giornale.test/feed", filtra=True)
    c = raccogli_fonte(conn, _rete(), fonte, PERIMETRO, [], {}, ADESSO)
    assert (c.trovati, c.nuovi, c.fuori, c.errore) == (3, 2, 1, None)
    scade = ADESSO + timedelta(days=7)
    assert _righe(conn, "giornale") == [
        ("https://giornale.test/a1", "C", ["elly-schlein"], True, scade, False),
        ("https://riservato.test/a3", "C", [], False, None, True),  # l'editore si oppone: niente testo
    ]
    # Al passaggio successivo gli stessi indirizzi non si rileggono
    c2 = raccogli_fonte(conn, _rete(), fonte, PERIMETRO, [], {}, ADESSO)
    assert (c2.trovati, c2.nuovi) == (3, 0)


def test_partito_tutto_e_testo_conservato(conn):
    fonte = Fonte("partito", "A", "rss", "https://partito.test/feed")
    c = raccogli_fonte(conn, _rete(), fonte, PERIMETRO, [], {}, ADESSO)
    # Dai partiti si tiene tutto, anche ciò che non nomina nessuno del perimetro, con il testo per sempre
    assert (c.nuovi, c.fuori) == (3, 0)
    assert all(r[3] and r[4] is None for r in _righe(conn, "partito"))


def test_doppione_per_impronta(conn):
    sql = """insert into core.documento_grezzo (fonte, livello, canale, url, dominio, sha256, testo)
             values ('partito', 'A', 'telegram', %s, 'x', %s, 't') on conflict do nothing"""
    assert conn.execute(sql, ("https://t.me/x/1", "b" * 64)).rowcount == 1
    assert conn.execute(sql, ("https://t.me/x/2", "b" * 64)).rowcount == 0


def test_fonte_che_non_risponde(conn):
    c = raccogli_fonte(
        conn, _rete(), Fonte("rotta", "C", "rss", "https://giornale.test/manca"), PERIMETRO, [], {}, ADESSO
    )
    assert c.errore and c.trovati == 0
    registra(conn, c)
    assert conn.execute("select fonte, nuovi, errore is not null from core.raccolta").fetchone() == ("rotta", 0, True)


def test_cancellazione_dei_testi_scaduti(conn):
    raccogli_fonte(
        conn,
        _rete(),
        Fonte("giornale", "C", "rss", "https://giornale.test/feed", filtra=True),
        PERIMETRO,
        [],
        {},
        ADESSO,
    )
    assert cancella_scaduti(conn, ADESSO + timedelta(days=6)) == 0
    assert cancella_scaduti(conn, ADESSO + timedelta(days=7)) == 1
    riga = conn.execute(
        "select testo, testo_cancellato_il, titolo from core.documento_grezzo where url = 'https://giornale.test/a1'"
    ).fetchone()
    assert riga == (None, ADESSO + timedelta(days=7), "Schlein: salario minimo subito")  # il resto rimane


def test_solo_la_cancellazione_del_testo_e_permessa(conn):
    conn.execute(
        """insert into core.documento_grezzo (fonte, livello, canale, url, dominio, sha256, testo)
           values ('p', 'A', 'rss', 'https://p.test/1', 'p.test', %s, 'testo')""",
        ("c" * 64,),
    )
    with pytest.raises(RaiseException):
        with conn.transaction():
            conn.execute("update core.documento_grezzo set titolo = 'cambiato'")
    with pytest.raises(RaiseException):
        with conn.transaction():
            conn.execute("delete from core.documento_grezzo")
    conn.execute("update core.documento_grezzo set testo = null, testo_cancellato_il = now()")


def test_giornale_senza_scadenza_rifiutato(conn):
    with pytest.raises(CheckViolation):
        conn.execute(
            """insert into core.documento_grezzo (fonte, livello, canale, url, dominio, sha256, testo)
               values ('g', 'C', 'rss', 'https://g.test/1', 'g.test', %s, 'testo')""",
            ("d" * 64,),
        )
