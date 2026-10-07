import json
from datetime import date

import httpx

from op_workers.rilascio.crea import domande, quando, scrivi, soggetti
from op_workers.rilascio.pubblica import _client, pubblica

PARTITI = {
    "partiti": [
        {"slug": "aa", "nome": "Partito A", "ruolo": [{"valore": "governo", "valido_dal": "2022-10-22"}]},
        {"slug": "bb", "nome": "Partito B", "ruolo": [
            {"valore": "governo", "valido_dal": "2022-10-22", "valido_al": "2023-12-31"},
            {"valore": "opposizione", "valido_dal": "2024-01-01"}]},
    ]
}  # fmt: skip
PERIMETRO = {"partiti": [{"slug": "aa"}, {"slug": "bb"}], "persone": [{"slug": "mario-rossi", "partito": "bb"}]}
ALIAS = {"mario-rossi": {"slug": "mario-rossi", "nome": "Mario", "cognome": "Rossi", "cariche": [
    {"carica": "Ministro", "valido_dal": "2022-10-22", "valido_al": "2023-12-31"},
    {"carica": "Segretario del partito", "valido_dal": "2020-01-01"}]}}  # fmt: skip


def test_soggetti_con_ruolo_di_oggi():
    s = soggetti(PARTITI, PERIMETRO, ALIAS, date(2026, 10, 7))
    assert [(x["id"], x["tipo"], x["ruolo"]) for x in s] == [
        ("aa", "partito", "Al governo"),
        ("bb", "partito", "All'opposizione"),
        ("mario-rossi", "persona", "Partito B · Segretario del partito"),
    ]
    assert s[2]["nome"] == "Mario Rossi"
    assert s[2]["partito"] == "bb"


def test_domande_solo_attive_e_senza_catalogo():
    assert domande(None) == []
    cat = {"enunciati": [
        {"id": "e-1", "testo": "Uno", "tema": "t", "contesto": {"fatto": "f", "favorevoli": "a", "contrari": "b"},
         "stato": "attivo"},
        {"id": "e-2", "testo": "Due", "tema": "t", "contesto": {}, "stato": "ritirato"}]}  # fmt: skip
    assert [d["id"] for d in domande(cat)] == ["e-1"]


def test_quando():
    assert quando("senato", date(2023, 5, 11)) == "Senato, 11 maggio 2023"


def test_scrivi_mette_le_impronte(tmp_path):
    m = scrivi({"manifest.json": {"versione": "x"}, "soggetti.json": []}, tmp_path)
    assert m["file"]["soggetti.json"].startswith("sha256:")
    assert json.loads((tmp_path / "manifest.json").read_text())["file"] == m["file"]


def test_pubblica_carica_versione_e_puntatore(tmp_path):
    scrivi({"manifest.json": {"versione": "2026.10.07-1200"}, "soggetti.json": []}, tmp_path)
    chiamate = []

    def gestore(req: httpx.Request) -> httpx.Response:
        chiamate.append((req.method, req.url.path, req.headers.get("x-upsert")))
        assert req.headers["apikey"] == "segreta"
        if req.url.path.endswith("/bucket"):
            return httpx.Response(400, json={"message": "The resource already exists"})
        return httpx.Response(200, json={})

    with _client("https://x.supabase.co", "segreta", httpx.MockTransport(gestore)) as c:
        pubblica(tmp_path, c)
    percorsi = [p for _, p, _ in chiamate]
    assert "/storage/v1/object/rilasci/2026.10.07-1200/soggetti.json" in percorsi
    assert "/storage/v1/object/rilasci/2026.10.07-1200/manifest.json" in percorsi
    assert chiamate[-1] == ("POST", "/storage/v1/object/rilasci/corrente.json", "true")
