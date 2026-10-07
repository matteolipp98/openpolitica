from datetime import date

from op_workers.anagrafica.sincronizza import sincronizza
from op_workers.connettori.base import AdesioneGrezza, ParlamentareGrezzo, VotazioneGrezza, VotoGrezzo
from op_workers.connettori.importa_voti import importa


def test_sincronizza_contenuti_veri_ed_e_idempotente(conn):
    primo = sincronizza(conn)
    assert primo.inseriti["persona"] == 10
    assert primo.inseriti["gruppo_parlamentare"] >= 18
    secondo = sincronizza(conn)
    assert sum(secondo.inseriti.values()) == 0
    # Meloni collegata al suo identificativo della Camera
    assert (
        conn.execute(
            """select p.slug from core.persona p join core.persona_id_esterno e on e.persona_id = p.id
           where e.fonte = 'camera' and e.id_esterno = '302103'"""
        ).fetchone()[0]
        == "giorgia-meloni"
    )


def test_gruppo_comune_azione_italia_viva_ha_due_partiti_fino_al_2023(conn):
    sincronizza(conn)
    righe = conn.execute(
        """select p.slug, gp.valido_al from core.gruppo_partito gp
           join core.gruppo_parlamentare g on g.id = gp.gruppo_id join core.partito p on p.id = gp.partito_id
           where g.ramo = 'camera' and g.id_esterno = 'gr4135' order by gp.valido_dal, p.slug"""
    ).fetchall()
    assert righe == [("azione", date(2023, 11, 19)), ("italia-viva", date(2023, 11, 19)), ("azione", None)]


V = VotazioneGrezza(
    ramo="camera",
    legislatura=19,
    id_esterno="vs19_1_1",
    data=date(2024, 1, 10),
    tipo="Finale atto Camera",
    titolo=None,
    descrizione="DDL 1 - VOTO FINALE",
    atto_ref="C.1",
    atto_titolo="Legge di prova",
    finale=True,
    fiducia=False,
    segreta=False,
    favorevoli=2,
    contrari=1,
    astenuti=0,
    approvata=True,
    url="https://x",
)


class ConnettoreFinto:
    ramo = "camera"

    def __init__(self, voti):
        self._voti = voti

    def parlamentari(self, leg):
        yield ParlamentareGrezzo("camera", "302103", "Giorgia", "Meloni")
        yield ParlamentareGrezzo("camera", "999001", "Anna", "Bianchi")
        yield ParlamentareGrezzo("camera", "999002", "Luca", "Verdi")

    def adesioni(self, leg):
        yield AdesioneGrezza("camera", "999001", "gr4133", date(2022, 10, 18), None)

    def votazioni(self, leg, dal):
        yield V

    def voti_del_giorno(self, leg, giorno):
        yield from self._voti


def _voti(*righe):
    return [VotoGrezzo("vs19_1_1", p, e, "gr4133") for p, e in righe]


def test_import_voti(conn):
    sincronizza(conn)
    c = ConnettoreFinto(
        _voti(("302103", "favorevole"), ("999001", "favorevole"), ("999002", "contrario"), ("777777", "assente"))
    )
    r = importa(conn, c, 19)
    assert (r.persone_nuove, r.votazioni_nuove, r.voti_nuovi, r.non_attribuiti) == (2, 1, 3, 1)
    assert r.incoerenti == []
    assert conn.execute("select coerente from core.votazione where id_esterno = 'vs19_1_1'").fetchone()[0] is True
    # persona automatica, mai fusa con altre
    assert conn.execute("select count(*) from core.persona where slug = 'camera-999001'").fetchone()[0] == 1
    # seconda esecuzione: niente di nuovo
    r2 = importa(conn, c, 19)
    assert (r2.persone_nuove, r2.votazioni_nuove, r2.voti_nuovi) == (0, 0, 0)


def test_votazione_incoerente_viene_marcata(conn):
    sincronizza(conn)
    r = importa(conn, ConnettoreFinto(_voti(("302103", "favorevole"))), 19)
    assert r.incoerenti == ["camera:vs19_1_1"]
    assert conn.execute("select coerente from core.votazione where id_esterno = 'vs19_1_1'").fetchone()[0] is False
