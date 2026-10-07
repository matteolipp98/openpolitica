from datetime import date
from decimal import Decimal

from op_workers.anagrafica.sincronizza import sincronizza
from op_workers.catalogo.candidati import candidate
from op_workers.posizioni.da_voti import Parametri

P = Parametri(Decimal("0.5"), 3, 19)
PERIMETRO = {"fratelli-d-italia", "partito-democratico", "lega", "movimento-5-stelle"}


def _votazione(conn, ide, fav, con, gruppi, titolo="Legge sul salario minimo", giorno=date(2024, 2, 1), ramo="camera"):
    vid = conn.execute(
        """insert into core.votazione (ramo, legislatura, id_esterno, data, finale, favorevoli, contrari, astenuti,
               url, atto_titolo, approvata)
           values (%s, 19, %s, %s, true, %s, %s, 0, 'https://x', %s, true) returning id""",
        (ramo, ide, giorno, fav, con, titolo),
    ).fetchone()[0]
    for g, f, c in gruppi:
        conn.execute(
            """insert into core.votazione_gruppo (votazione_id, gruppo_id, favorevoli, contrari)
               select %s, id, %s, %s from core.gruppo_parlamentare where ramo = %s and id_esterno = %s""",
            (vid, f, c, ramo, g),
        )


def test_candidate_divisive_con_partiti_opposti(conn):
    sincronizza(conn)
    _votazione(conn, "vs19_1_1", 180, 120, [("gr4133", 100, 0), ("gr4136", 0, 60)])  # FdI sì, PD no → buona
    _votazione(conn, "vs19_1_2", 290, 10, [("gr4133", 100, 0), ("gr4136", 60, 0)], titolo="Legge unanime")
    _votazione(conn, "vs19_1_3", 150, 150, [("gr4133", 100, 0), ("gr4132", 50, 0)], titolo="Altra legge")
    cands, scarti = candidate(conn, 19, PERIMETRO, P, 0.25)
    assert [c.id_esterno for c in cands] == ["vs19_1_1"]
    assert cands[0].orientamenti == {"fratelli-d-italia": 1, "partito-democratico": -1}
    assert scarti == {"poco divisiva (quasi tutti d'accordo)": 1, "nessun partito seguito a favore e uno contro": 1}


def test_stessa_legge_nei_due_rami_una_sola_domanda(conn):
    sincronizza(conn)
    _votazione(conn, "vs19_1_1", 180, 120, [("gr4133", 100, 0), ("gr4136", 0, 60)])
    _votazione(conn, "19-1-1", 100, 70, [("85", 60, 0), ("49", 0, 35)], giorno=date(2024, 3, 1), ramo="senato")
    cands, _ = candidate(conn, 19, PERIMETRO, P, 0.25)
    assert [c.id_esterno for c in cands] == ["19-1-1"]  # tiene la più recente
