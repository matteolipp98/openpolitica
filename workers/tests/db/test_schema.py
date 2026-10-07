import psycopg
import pytest
from psycopg.errors import CheckViolation, InsufficientPrivilege, RaiseException


def _persona(c, slug="mario-rossi"):
    return c.execute(
        "insert into core.persona (slug, nome, cognome) values (%s, 'Mario', 'Rossi') returning id", (slug,)
    ).fetchone()[0]


def _partito(c, slug):
    return c.execute("insert into core.partito (slug, nome) values (%s, %s) returning id", (slug, slug)).fetchone()[0]


def _gruppo(c, id_esterno="gr1"):
    return c.execute(
        "insert into core.gruppo_parlamentare (ramo, legislatura, id_esterno) values ('camera', 19, %s) returning id",
        (id_esterno,),
    ).fetchone()[0]


def _votazione(c, id_esterno="vs19_1_1"):
    return c.execute(
        """insert into core.votazione (ramo, legislatura, id_esterno, data, finale, favorevoli, contrari, astenuti, url)
           values ('camera', 19, %s, '2024-01-10', true, 10, 5, 1, 'https://example.org') returning id""",
        (id_esterno,),
    ).fetchone()[0]


def test_le_tabelle_pubblicate_sono_append_only(conn):
    v = _votazione(conn)
    with pytest.raises(RaiseException, match="append-only"):
        conn.execute("update core.votazione set favorevoli = 11 where id = %s", (v,))


def test_append_only_anche_sulla_cancellazione(conn):
    v = _votazione(conn)
    with pytest.raises(RaiseException, match="append-only"):
        conn.execute("delete from core.votazione where id = %s", (v,))


def test_votazione_unica_per_ramo_legislatura_id(conn):
    _votazione(conn, "vs19_9_9")
    with pytest.raises(psycopg.errors.UniqueViolation):
        _votazione(conn, "vs19_9_9")


def _enunciato(c):
    c.execute(
        """insert into core.enunciato (id, versione, catalogo_versione, testo, tema_id, livello_governo, stato,
                                       origine, test)
           values ('e-prova', 1, 'v1', 'Una misura di prova', 'economia', 'nazionale', 'attivo', '{}', '{}')"""
    )


def test_posizione_nulla_solo_se_non_documentata(conn):
    _enunciato(conn)
    p = _partito(conn, "p1")
    with pytest.raises(CheckViolation):
        conn.execute(
            """insert into core.posizione (soggetto_tipo, soggetto_id, enunciato_id, enunciato_versione, valore, stato,
                                           confidenza, origine, calcolo_versione)
               values ('partito', %s, 'e-prova', 1, null, 'documentata', null, 'voto', 'pos-voti-1')""",
            (p,),
        )


def test_posizione_corrente_prende_l_ultima_registrata(conn):
    _enunciato(conn)
    p = _partito(conn, "p1")
    for valore, quando in ((1, "2026-01-01"), (-2, "2026-02-01")):
        conn.execute(
            """insert into core.posizione (soggetto_tipo, soggetto_id, enunciato_id, enunciato_versione, valore, stato,
                                           confidenza, origine, calcolo_versione, registrato_il)
               values ('partito', %s, 'e-prova', 1, %s, 'documentata', 'piena', 'voto', 'pos-voti-1', %s)""",
            (p, valore, quando),
        )
    [(valore,)] = conn.execute("select valore from core.posizione_corrente where soggetto_id = %s", (p,)).fetchall()
    assert valore == -2


class TestPartitoAllaData:
    def test_gruppo_di_un_solo_partito(self, conn):
        persona, g, fdi = _persona(conn), _gruppo(conn), _partito(conn, "fdi")
        conn.execute(
            "insert into core.gruppo_partito (gruppo_id, partito_id, valido_dal) values (%s, %s, '2022-10-18')",
            (g, fdi),
        )
        assert conn.execute("select core.partito_alla_data(%s, %s, '2024-01-01')", (persona, g)).fetchone()[0] == fdi

    def test_gruppo_comune_usa_l_appartenenza_della_persona(self, conn):
        persona, g = _persona(conn), _gruppo(conn)
        az, iv = _partito(conn, "azione"), _partito(conn, "italia-viva")
        for partito in (az, iv):
            conn.execute(
                """insert into core.gruppo_partito (gruppo_id, partito_id, valido_dal, valido_al)
                   values (%s, %s, '2022-10-18', '2023-11-19')""",
                (g, partito),
            )
        conn.execute(
            """insert into core.appartenenza (persona_id, tipo, partito_id, valido_dal)
               values (%s, 'partito', %s, '2019-09-18')""",
            (persona, iv),
        )
        assert conn.execute("select core.partito_alla_data(%s, %s, '2023-05-01')", (persona, g)).fetchone()[0] == iv

    def test_senza_informazioni_non_attribuisce(self, conn):
        persona, g = _persona(conn), _gruppo(conn)
        assert conn.execute("select core.partito_alla_data(%s, %s, '2024-01-01')", (persona, g)).fetchone()[0] is None

    def test_fuori_dal_periodo_non_attribuisce(self, conn):
        persona, g, p = _persona(conn), _gruppo(conn), _partito(conn, "x")
        conn.execute(
            """insert into core.gruppo_partito (gruppo_id, partito_id, valido_dal, valido_al)
               values (%s, %s, '2022-10-18', '2023-11-19')""",
            (g, p),
        )
        assert conn.execute("select core.partito_alla_data(%s, %s, '2024-01-01')", (persona, g)).fetchone()[0] is None


class TestPermessi:
    def test_il_worker_non_puo_modificare_i_voti(self, conn):
        v = _votazione(conn)
        conn.execute("set local role op_worker")
        with pytest.raises((InsufficientPrivilege, RaiseException)):
            conn.execute("update core.votazione set contrari = 0 where id = %s", (v,))

    def test_il_worker_puo_inserire(self, conn):
        conn.execute("set local role op_worker")
        _votazione(conn, "vs19_2_2")

    def test_segnalazione_con_limiti(self, conn):
        assert conn.execute("select core.segnala('https://x.it/p', 'Il numero è sbagliato.')").fetchone()[0]
        with pytest.raises(CheckViolation):
            conn.execute("select core.segnala('https://x.it/p', 'corto')")
