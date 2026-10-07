from datetime import date

from op_workers.anagrafica.sincronizza import sincronizza
from op_workers.connettori.base import AdesioneGrezza, ParlamentareGrezzo, VotazioneGrezza, VotoGrezzo
from op_workers.connettori.importa_voti import conteggi, importa


def test_sincronizza_contenuti_veri_ed_e_idempotente(conn):
    primo = sincronizza(conn)
    assert primo.inseriti["persona"] == 10
    assert primo.inseriti["gruppo_parlamentare"] >= 18
    secondo = sincronizza(conn)
    assert sum(secondo.inseriti.values()) == 0
    # Meloni collegata al suo identificativo della Camera
    slug = conn.execute(
        """select p.slug from core.persona p join core.persona_id_esterno e on e.persona_id = p.id
           where e.fonte = 'camera' and e.id_esterno = '302103'"""
    ).fetchone()[0]
    assert slug == "giorgia-meloni"


def test_gruppo_comune_azione_italia_viva_ha_due_partiti_fino_al_2023(conn):
    sincronizza(conn)
    righe = conn.execute(
        """select p.slug, gp.valido_al from core.gruppo_partito gp
           join core.gruppo_parlamentare g on g.id = gp.gruppo_id join core.partito p on p.id = gp.partito_id
           where g.ramo = 'camera' and g.id_esterno = 'gr4135' order by gp.valido_dal, p.slug"""
    ).fetchall()
    assert righe == [("azione", date(2023, 11, 19)), ("italia-viva", date(2023, 11, 19)), ("azione", None)]


def test_conteggi():
    assert conteggi(["favorevole", "favorevole", "contrario", "assente", "votante_segreto"]) == (2, 1, 0, 2)


def _votazione(id_esterno="vs19_1_1", giorno=date(2023, 1, 10), fav=3, con=1, ast=0):
    return VotazioneGrezza(
        ramo="camera",
        legislatura=19,
        id_esterno=id_esterno,
        data=giorno,
        tipo="Finale atto Camera",
        titolo=None,
        descrizione="DDL 1 - VOTO FINALE",
        atto_ref="C.1",
        atto_titolo="Legge di prova",
        finale=True,
        fiducia=False,
        segreta=False,
        favorevoli=fav,
        contrari=con,
        astenuti=ast,
        approvata=True,
        url="https://x",
    )


class ConnettoreFinto:
    ramo = "camera"

    def __init__(self, voti, votazione=None):
        self._voti, self._v = voti, votazione or _votazione()

    def parlamentari(self, leg):
        yield ParlamentareGrezzo("camera", "302103", "Giorgia", "Meloni")
        yield ParlamentareGrezzo("camera", "999001", "Anna", "Bianchi")
        yield ParlamentareGrezzo("camera", "999002", "Luca", "Verdi")
        yield ParlamentareGrezzo("camera", "999003", "Sara", "Neri")

    def adesioni(self, leg):
        yield AdesioneGrezza("camera", "999001", "gr4133", date(2022, 10, 18), None)

    def votazioni(self, leg, dal):
        yield self._v

    def voti_del_giorno(self, leg, giorno):
        yield from self._voti


def _voti(*righe):
    return [VotoGrezzo("vs19_1_1", p, e, g) for p, e, g in righe]


def test_import_salva_conteggi_per_gruppo_e_voto_individuale_solo_dove_serve(conn):
    sincronizza(conn)
    voti = _voti(
        ("302103", "favorevole", "gr4133"),  # Meloni: perimetro → voto individuale
        ("999001", "favorevole", "gr4133"),  # FdI, fuori perimetro → solo conteggio
        ("999002", "contrario", "gr4135"),  # gruppo Azione-Italia Viva nel 2023 → voto individuale
        ("999003", "favorevole", "gr4135"),
        ("777777", "assente", "gr4111"),  # identificativo sconosciuto
    )
    r = importa(conn, ConnettoreFinto(voti), 19)
    assert r.incoerenti == []
    assert (r.votazioni_nuove, r.voti_individuali, r.non_attribuiti) == (1, 3, 1)

    per_gruppo = dict(
        (g, (f, c, a, x))
        for g, f, c, a, x in conn.execute(
            """select g.id_esterno, vg.favorevoli, vg.contrari, vg.astenuti, vg.altri from core.votazione_gruppo vg
               join core.gruppo_parlamentare g on g.id = vg.gruppo_id"""
        )
    )
    assert per_gruppo == {"gr4133": (2, 0, 0, 0), "gr4135": (1, 1, 0, 0), "gr4111": (0, 0, 0, 1)}
    assert conn.execute("select count(*) from core.persona where slug = 'camera-999001'").fetchone()[0] == 1

    r2 = importa(conn, ConnettoreFinto(voti), 19)  # seconda esecuzione: niente di nuovo
    assert (r2.persone_nuove, r2.votazioni_nuove, r2.voti_individuali) == (0, 0, 0)


def test_dopo_la_divisione_il_gruppo_azione_non_salva_voti_individuali(conn):
    sincronizza(conn)
    v = _votazione(giorno=date(2024, 3, 1), fav=1, con=0)
    r = importa(conn, ConnettoreFinto(_voti(("999002", "favorevole", "gr4135")), v), 19)
    assert (r.voti_individuali, r.conteggi_gruppo) == (0, 1)


def test_votazione_incoerente_viene_marcata(conn):
    sincronizza(conn)
    r = importa(conn, ConnettoreFinto(_voti(("302103", "favorevole", "gr4133"))), 19)
    assert r.incoerenti == ["camera:vs19_1_1"]
    assert conn.execute("select coerente from core.votazione where id_esterno = 'vs19_1_1'").fetchone()[0] is False


def test_blocco_della_fonte_ferma_senza_errore_e_tiene_i_giorni_fatti(conn):
    from op_workers.comuni.sparql import ErroreSparql

    sincronizza(conn)

    class Bloccato(ConnettoreFinto):
        def votazioni(self, leg, dal):
            yield _votazione("vs19_1_1", date(2023, 1, 10), fav=1, con=0)
            yield _votazione("vs19_2_1", date(2023, 1, 11), fav=1, con=0)

        def voti_del_giorno(self, leg, giorno):
            if giorno == date(2023, 1, 11):
                raise ErroreSparql("https://dati.senato.it/sparql: HTTP 403")
            yield VotoGrezzo("vs19_1_1", "302103", "favorevole", "gr4133")

    r = importa(conn, Bloccato([]), 19)
    assert r.interrotto and "2023-01-11" in r.interrotto
    assert r.votazioni_nuove == 1
    assert conn.execute("select count(*) from core.votazione").fetchone()[0] == 1
