from decimal import Decimal

import pytest

from op_workers.posizioni.da_voti import (
    Evidenza,
    Parametri,
    arrotonda,
    orientamento_gruppo,
    orientamento_persona,
    posizione,
)

P = Parametri(Decimal("0.5"), 3, 19)


def ev(o, data="2024-01-01", leg=19, vid=None):
    return Evidenza(vid or f"v{data}{o}", data, leg, o)


@pytest.mark.parametrize(
    ("espr", "atteso"),
    [("favorevole", 1), ("contrario", -1), ("astenuto", 0), ("in_missione", None), ("non_votante", None)],
)
def test_orientamento_persona(espr, atteso):
    assert orientamento_persona(espr) == atteso


@pytest.mark.parametrize(
    ("fav", "con", "ast", "atteso"),
    [
        (10, 0, 0, 1),
        (3, 1, 0, 1),  # q = 0,5: esattamente la soglia → a favore
        (1, 3, 0, -1),  # q = -0,5 → contro
        (5, 4, 0, 0),  # diviso
        (0, 0, 10, 0),  # tutti astenuti
        (1, 1, 0, None),  # meno dei membri minimi
    ],
)
def test_orientamento_gruppo(fav, con, ast, atteso):
    voti = ["favorevole"] * fav + ["contrario"] * con + ["astenuto"] * ast + ["in_missione"] * 7
    assert orientamento_gruppo(voti, P) == atteso


def test_orientamento_gruppo_simmetrico():
    for fav in range(8):
        for con in range(8):
            a = orientamento_gruppo(["favorevole"] * fav + ["contrario"] * con, P)
            b = orientamento_gruppo(["favorevole"] * con + ["contrario"] * fav, P)
            assert (a is None and b is None) or a == -b


@pytest.mark.parametrize(("x", "atteso"), [("0.5", 1), ("-0.5", -1), ("1.49", 1), ("-1.5", -2), ("0", 0)])
def test_arrotonda_lontano_da_zero(x, atteso):
    assert arrotonda(Decimal(x)) == atteso


def test_posizione_media_dei_voti_correnti():
    pos = posizione([ev(1, "2023-01-01"), ev(1, "2024-01-01"), ev(0, "2024-02-01")], P)
    # media 2/3 → 2 × 0,667 = 1,33 → 1
    assert (pos.valore, pos.stato, pos.confidenza, pos.valido_dal) == (1, "documentata", "piena", "2024-02-01")


def test_voti_opposti_sono_divergenza_non_media_nascosta():
    pos = posizione([ev(1, "2023-01-01"), ev(-1, "2024-01-01")], P)
    assert pos.stato == "divergente"
    assert pos.valore == 0
    assert len(pos.evidenze) == 2


def test_fallback_alla_legislatura_precedente_con_confidenza_ridotta():
    pos = posizione([ev(-1, "2019-05-01", 18), ev(1, "2020-03-01", 18)], P)
    assert (pos.valore, pos.confidenza, pos.valido_dal) == (2, "ridotta", "2020-03-01")
    assert len(pos.evidenze) == 1


def test_i_voti_correnti_vincono_sui_precedenti():
    pos = posizione([ev(-1, "2020-01-01", 18), ev(1, "2024-01-01", 19)], P)
    assert (pos.valore, pos.confidenza) == (2, "piena")


def test_senza_voti_non_documentata():
    pos = posizione([], P)
    assert (pos.valore, pos.stato, pos.confidenza) == (None, "non_documentata", None)


def test_simmetria_della_posizione():
    evs = [ev(1, "2023-01-01"), ev(0, "2023-06-01"), ev(1, "2024-01-01")]
    neg = [Evidenza(e.votazione_id, e.data, e.legislatura, -e.orientamento) for e in evs]
    assert posizione(neg, P).valore == -posizione(evs, P).valore


def test_parametri_dal_file_di_contenuto():
    p = Parametri.da_contenuti(
        {"posizioni": {"quotaMaggioranzaGruppo": 0.5, "membriMinimi": 3, "legislaturaRiferimento": 19}}
    )
    assert p == P
