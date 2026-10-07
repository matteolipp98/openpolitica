from datetime import date

from op_workers.andamento.da_voti import (
    VotoPartito,
    calcola,
    prevalente,
    ruoli_da_righe,
    trimestre,
    trimestri_tra,
    unito,
)

GOV = ruoli_da_righe([("a", "governo", date(2022, 10, 22), None), ("b", "opposizione", date(2022, 10, 22), None)])


def v(vid, d, p, fav, con, ast=0):
    return VotoPartito(vid, d, p, fav, con, ast)


def test_trimestri():
    assert trimestre(date(2024, 4, 1)) == "2024-T2"
    assert trimestri_tra(date(2022, 11, 3), date(2023, 4, 2)) == ["2022-T4", "2023-T1", "2023-T2"]


def test_prevalente_e_unito():
    assert prevalente(10, 2, 0) == "favorevole"
    assert prevalente(5, 5, 0) is None  # pari merito in testa: nessuna scelta
    assert prevalente(0, 0, 0) is None
    assert unito(9, 1, 0)  # 9 su 10
    assert not unito(8, 2, 0)


def test_vota_con_governo_e_unito():
    voti = [
        v("1", date(2023, 1, 10), "a", 30, 0),
        v("1", date(2023, 1, 10), "b", 2, 18),
        v("2", date(2023, 2, 10), "a", 30, 0),
        v("2", date(2023, 2, 10), "b", 15, 5),
        v("3", date(2023, 5, 10), "a", 0, 30),
        v("3", date(2023, 5, 10), "b", 1, 1),  # b sotto i membri minimi
    ]
    r = calcola(voti, GOV, membri_minimi=3)
    assert r["trimestri"] == ["2023-T1", "2023-T2"]
    assert r["serie"]["b"]["vota_con_governo"] == [{"n": 1, "d": 2}, {"n": 0, "d": 0}]
    assert r["serie"]["b"]["vota_compatto"] == [{"n": 1, "d": 2}, {"n": 0, "d": 0}]  # 18 su 20 sì, 15 su 20 no
    assert r["serie"]["a"]["vota_con_governo"] == [{"n": 2, "d": 2}, {"n": 1, "d": 1}]
    assert r["governo"] == {"a": [True, True], "b": [False, False]}


def test_pari_merito_del_partito_non_conta_per_il_governo():
    r = calcola([v("1", date(2023, 1, 10), "a", 30, 0), v("1", date(2023, 1, 10), "b", 5, 5)], GOV, 3)
    assert r["serie"]["b"]["vota_con_governo"] == [{"n": 0, "d": 0}]
    assert r["serie"]["b"]["vota_compatto"] == [{"n": 0, "d": 1}]


def test_ruolo_cambia_nel_tempo():
    gov = ruoli_da_righe(
        [("c", "opposizione", date(2022, 10, 22), date(2023, 12, 31)), ("c", "governo", date(2024, 1, 1), None)]
    )
    r = calcola([v("1", date(2023, 11, 1), "c", 5, 0), v("2", date(2024, 2, 1), "c", 5, 0)], gov, 3)
    assert r["governo"]["c"] == [False, True]


def test_niente_voti():
    assert calcola([], GOV, 3)["trimestri"] == []
