"""Test di contratto sulle fonti vere (ADR 0025). Girano solo con -m contratto, in GitHub Actions.

Usano votazioni note, verificate con la sonda del 2026-10-07: se falliscono, la fonte è cambiata.
"""

from datetime import date

import pytest

from op_workers.connettori.camera import ConnettoreCamera
from op_workers.connettori.senato import ConnettoreSenato

pytestmark = pytest.mark.contratto


def test_camera_voti_tornano_con_i_totali():
    c = ConnettoreCamera()
    [v] = [x for x in c.votazioni(19, date(2026, 10, 1)) if x.id_esterno == "vs19_718_011"]
    voti = [x for x in c.voti_del_giorno(19, date(2026, 10, 1)) if x.id_votazione_esterno == "vs19_718_011"]
    conta = {e: sum(1 for x in voti if x.espressione == e) for e in ("favorevole", "contrario", "astenuto")}
    assert (conta["favorevole"], conta["contrario"], conta["astenuto"]) == (v.favorevoli, v.contrari, v.astenuti)


def test_camera_parlamentari_e_adesioni():
    c = ConnettoreCamera()
    ids = {p.id_esterno for p in c.parlamentari(19)}
    assert {"302103", "308930"} <= ids  # Meloni, Schlein
    gruppi_meloni = {a.id_gruppo_esterno for a in c.adesioni(19) if a.id_persona_esterno == "302103"}
    assert "gr4133" in gruppi_meloni


def test_senato_voti_tornano_con_i_totali():
    s = ConnettoreSenato()
    [v] = [x for x in s.votazioni(19, date(2024, 3, 12)) if x.id_esterno == "19-167-42"]
    voti = [x for x in s.voti_del_giorno(19, date(2024, 3, 12)) if x.id_votazione_esterno == "19-167-42"]
    assert sum(1 for x in voti if x.espressione == "favorevole") == v.favorevoli == 86
    assert sum(1 for x in voti if x.espressione == "contrario") == v.contrari == 49


def test_senato_parlamentari_e_adesioni():
    s = ConnettoreSenato()
    assert {"25407", "30742", "30110"} <= {p.id_esterno for p in s.parlamentari(19)}
    calenda = sorted((a.dal, a.id_gruppo_esterno) for a in s.adesioni(19) if a.id_persona_esterno == "30110")
    assert [g for _, g in calenda] == ["91", "9"]
