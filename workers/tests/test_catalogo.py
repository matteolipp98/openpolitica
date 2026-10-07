from datetime import date

import httpx
import pytest

from op_workers.catalogo import genera
from op_workers.catalogo.candidati import Candidata
from op_workers.catalogo.gemini import Gemini, QuotaEsaurita

TEMI = [{"id": f"t{i}", "nome": f"Tema {i}", "descrizione": "x"} for i in range(6)]


def cand(ide="vs19_1_1", data=date(2024, 1, 1), fav=200, con=100):
    return Candidata("u", "camera", ide, data, "C.1", "Legge sul salario minimo", True, fav, con, 0,
                     {"pd": 1, "fdi": -1})  # fmt: skip


GEN = {"id": "vs19_1_1", "scarta": False, "tema": "t1", "enunciato": "Serve un salario minimo per legge.",
       "opposto": "Non serve un salario minimo per legge.", "varianti": ["V1", "V2"],
       "favorevoli": "Chi è a favore dice A.", "contrari": "Chi è contro dice B."}  # fmt: skip


def test_la_verifica_non_vede_quale_frase_e_l_originale():
    prompt, mappa = genera.prompt_verifica([(cand(), GEN)], TEMI, "s")
    assert "enunciato" not in prompt and "opposto" not in prompt.split("<atti>")[1]
    ruoli = sorted(r for k, (_, r) in mappa.items() if "F" in k)
    assert ruoli == ["enunciato", "opposto", "variante", "variante"]


def test_ordine_dei_temi_cambia_tra_lotti_ma_e_riproducibile():
    assert genera.temi_ruotati(TEMI, "a") == genera.temi_ruotati(TEMI, "a")
    assert len({genera.temi_ruotati(TEMI, s).splitlines()[0] for s in "abcdefgh"}) > 1


@pytest.mark.parametrize(
    ("risposte", "tema", "atteso"),
    [
        ([("enunciato", "d_accordo"), ("variante", "d_accordo"), ("variante", "d_accordo"), ("opposto", "contrario")],
         "t1", (True, True, True)),
        ([("enunciato", "d_accordo"), ("variante", "contrario"), ("variante", "d_accordo"), ("opposto", "contrario")],
         "t1", (True, False, True)),
        ([("enunciato", "d_accordo"), ("variante", "d_accordo"), ("variante", "d_accordo"), ("opposto", "d_accordo")],
         "t2", (False, True, False)),
    ],
)  # fmt: skip
def test_test_di_tema_sensibilita_polarita(risposte, tema, atteso):
    e = genera.costruisci_enunciato(cand(), GEN, {"tema": tema, "risposte": risposte}, "gemini-x")
    assert (
        e["test"]["tema"]["superato"],
        e["test"]["sensibilita"]["superato"],
        e["test"]["polarita"]["superato"],
    ) == atteso
    assert e["id"] == "e-camera-vs19-1-1"
    assert e["contesto"]["fatto"] == "Se n'è votato alla Camera il 1 gennaio 2024: la legge è stata approvata."


def test_selezione_bilanciata_per_tema():
    def e(tema, minoranza, data):
        return {"tema": tema, "origine": {"data": data}, "test": {"divisivita": {"dettagli": {"minoranza": minoranza}}}}

    voci = [e("a", 0.3, "2024-01-01"), e("a", 0.4, "2023-01-01"), e("a", 0.3, "2025-01-01"), e("b", 0.3, "2024-01-01"),
            e("b", 0.5, "2024-02-01")]  # fmt: skip
    scelti, k = genera.seleziona(voci, ["a", "b"], 5)
    assert k == 2
    assert [(x["tema"], x["origine"]["data"]) for x in scelti] == [
        ("a", "2023-01-01"), ("a", "2025-01-01"), ("b", "2024-02-01"), ("b", "2024-01-01")]  # fmt: skip


def _gemini(gestore, **kw):
    return Gemini(
        chiave="k", client=httpx.Client(transport=httpx.MockTransport(gestore)), pausa=0, attesa_errori=0, **kw
    )


def test_quota_giornaliera_ferma_senza_errore():
    g = _gemini(lambda req: httpx.Response(429, text='{"quotaId": "GenerateRequestsPerDayPerProjectPerModel"}'))
    with pytest.raises(QuotaEsaurita):
        g.json("p", {})


def test_timeout_si_riprova_poi_ferma_senza_errore():
    """Un timeout non fa fallire il job: si riprova e, se continua, ci si ferma come per la quota (#69)."""
    tentativi = []

    def sempre_timeout(req):
        tentativi.append(req)
        raise httpx.ReadTimeout("timed out", request=req)

    with pytest.raises(QuotaEsaurita):
        _gemini(sempre_timeout).json("p", {})
    assert len(tentativi) == 4

    risposte = iter([None, httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "[2]"}]}}]})])

    def poi_risponde(req):
        r = next(risposte)
        if r is None:
            raise httpx.ReadTimeout("timed out", request=req)
        return r

    assert _gemini(poi_risponde).json("p", {}).dati == [2]


def test_tetto_di_chiamate_e_cache(tmp_path):
    chiamate = []

    def gestore(req):
        chiamate.append(req)
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "[1]"}]}}],
                                         "usageMetadata": {"promptTokenCount": 3}})  # fmt: skip

    g = _gemini(gestore, max_chiamate=1)
    cache = genera.Cache(tmp_path)
    assert genera.chiama(g, cache, "genera", "stesso prompt", {}, None)["risposta"] == [1]
    assert genera.chiama(g, cache, "genera", "stesso prompt", {}, None)["risposta"] == [1]  # dalla cache
    assert len(chiamate) == 1
    with pytest.raises(QuotaEsaurita):
        genera.chiama(g, cache, "genera", "altro prompt", {}, None)
