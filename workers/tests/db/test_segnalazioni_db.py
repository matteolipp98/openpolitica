import psycopg
import pytest


def _segnala(c, testo="Il dato sulla Camera è sbagliato", trappola=None, ip="1.2.3.4"):
    c.execute("select set_config('request.headers', %s, true)", (f'{{"x-forwarded-for": "{ip}, 10.0.0.1"}}',))
    return c.execute("select public.segnala('/partiti/lega', %s, null, %s)", (testo, trappola)).fetchone()[0]


def test_salva_senza_indirizzo(conn):
    assert _segnala(conn) == {"ok": True}
    testo, origine = conn.execute("select testo, origine from core.segnalazione").fetchone()
    assert testo.startswith("Il dato") and len(origine) == 64 and "1.2.3.4" not in origine


def test_trappola_finge_successo_e_non_salva(conn):
    assert _segnala(conn, trappola="http://spam") == {"ok": True}
    assert conn.execute("select count(*) from core.segnalazione").fetchone()[0] == 0


def test_massimo_cinque_all_ora_per_indirizzo(conn):
    for _ in range(5):
        _segnala(conn)
    _segnala(conn, ip="5.6.7.8")  # un altro indirizzo passa
    with pytest.raises(psycopg.errors.ProgramLimitExceeded):
        _segnala(conn)


def test_testo_troppo_corto(conn):
    with pytest.raises(psycopg.errors.InvalidParameterValue):
        _segnala(conn, testo="no")
