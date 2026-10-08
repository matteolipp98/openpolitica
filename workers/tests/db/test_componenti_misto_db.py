"""Componenti del misto nel database: appartenenze di partito e seggi (issue #78)."""

from datetime import date

from op_workers.anagrafica.componenti_misto import sincronizza_componenti
from op_workers.anagrafica.sincronizza import leggi
from op_workers.rilascio.crea import parlamento

CAM = "http://dati.camera.it/ocd/"


class SparqlFinto:
    def __init__(self, righe):
        self.righe, self.query = righe, []

    def select(self, q):
        self.query.append(q)
        return self.righe


def _partiti(c):
    for p in leggi("partiti.yaml")["partiti"]:
        c.execute(
            "insert into core.partito (slug, nome) values (%s, %s) on conflict do nothing", (p["slug"], p["nome"])
        )


def _persona(c, ramo, ide, gruppo, dal="2022-10-18"):
    pe = c.execute(
        "insert into core.persona (slug, nome, cognome) values (%s, 'N', 'C') returning id", (f"{ramo}-{ide}",)
    ).fetchone()[0]
    c.execute(
        """insert into core.persona_id_esterno (persona_id, fonte, id_esterno, valido_dal)
           values (%s, %s, %s, '2022-10-13')""",
        (pe, ramo, ide),
    )
    c.execute(
        "insert into core.appartenenza (persona_id, tipo, gruppo_id, valido_dal) values (%s, 'gruppo', %s, %s)",
        (pe, gruppo, dal),
    )
    return pe


def _gruppo(c, ramo, ide):
    return c.execute(
        "insert into core.gruppo_parlamentare (ramo, legislatura, id_esterno) values (%s, 19, %s) returning id",
        (ramo, ide),
    ).fetchone()[0]


def test_misto_attribuito_alle_componenti(conn):
    _partiti(conn)
    misto_s, misto_c = _gruppo(conn, "senato", "9"), _gruppo(conn, "camera", "gr4111")
    for ide in ("22918", "36390", "36437", "28543"):  # tre AVS e Monti, senatore a vita
        _persona(conn, "senato", ide, misto_s)
    calenda = _persona(conn, "senato", "30110", misto_s, dal="2023-11-09")
    # Calenda ha già l'appartenenza da leader del perimetro: due righe dello stesso partito non lo annullano
    conn.execute(
        """insert into core.appartenenza (persona_id, tipo, partito_id, valido_dal, fonte_url)
           select %s, 'partito', id, '2022-10-13', 'content/perimetro.yaml' from core.partito where slug = 'azione'""",
        (calenda,),
    )
    _persona(conn, "camera", "307436", misto_c)  # Magi, +Europa
    _persona(conn, "camera", "305580", misto_c)  # minoranze linguistiche

    righe = [
        {"c": f"{CAM}componenteGruppoMisto.rdf/cgm4139", "dep": f"{CAM}deputato.rdf/d307436_19", "ini": "20221019"},
        {"c": f"{CAM}componenteGruppoMisto.rdf/cgm4137", "dep": f"{CAM}deputato.rdf/d305580_19", "ini": "20221019"},
    ]
    e = sincronizza_componenti(conn, SparqlFinto(righe))
    assert e.inserite == 5  # Magi + tre AVS + Calenda; le altre persone del file non sono nel database
    assert "senato:36436" in e.persone_mancanti
    assert not e.componenti_sconosciute
    # Idempotente
    assert sincronizza_componenti(conn, SparqlFinto(righe)).inserite == 0

    fonte = conn.execute(
        """select a.fonte_url from core.appartenenza a join core.persona p on p.id = a.persona_id
           where p.slug = 'senato-22918' and a.tipo = 'partito'"""
    ).fetchone()[0]
    assert fonte.startswith("https://www.senato.it/") and fonte.endswith("did=22918")

    out = parlamento(conn, ["alleanza-verdi-e-sinistra", "azione", "piu-europa"], 19, date(2026, 10, 8))
    assert out["rami"]["senato"] == {
        "totale": 5,
        "partiti": {"alleanza-verdi-e-sinistra": 3, "azione": 1, "piu-europa": 0},
        "altri": 1,
    }
    assert out["rami"]["camera"]["partiti"]["piu-europa"] == 1
    assert out["rami"]["camera"]["altri"] == 1


def test_floridia_fuori_dalla_componente_non_si_attribuisce(conn):
    _partiti(conn)
    misto = _gruppo(conn, "senato", "9")
    pe = _persona(conn, "senato", "36399", misto)
    sincronizza_componenti(conn, SparqlFinto([]))
    avs = conn.execute("select id from core.partito where slug = 'alleanza-verdi-e-sinistra'").fetchone()[0]
    prima = conn.execute("select core.partito_alla_data(%s, %s, '2024-01-10')", (pe, misto)).fetchone()[0]
    dopo = conn.execute("select core.partito_alla_data(%s, %s, '2025-03-01')", (pe, misto)).fetchone()[0]
    assert (prima, dopo) == (avs, None)
