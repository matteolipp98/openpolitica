from datetime import date

import pytest

from op_workers.anagrafica.componenti_misto import Esito, adesioni_camera, adesioni_senato
from op_workers.anagrafica.sincronizza import leggi
from op_workers.connettori.base import DatoInatteso

CAM = "http://dati.camera.it/ocd/"


def riga(cgm, dep, ini, fin=None):
    r = {"c": f"{CAM}componenteGruppoMisto.rdf/{cgm}", "dep": f"{CAM}deputato.rdf/d{dep}_19", "ini": ini}
    if fin:
        r["fin"] = fin
    return r


def test_camera_componente_con_partito_senza_partito_e_sconosciuta():
    e = Esito()
    righe = [
        riga("cgm4139", "307436", "20221019"),
        riga("cgm4139", "307436", "20221019"),  # il dataset ripete le righe
        riga("cgm4138", "302080", "20221019", "20221027"),
        riga("cgm4137", "305580", "20221019"),  # minoranze linguistiche: nessun partito
        riga("cgm9999", "300001", "20260101"),  # componente nuova: si segnala, non si attribuisce
    ]
    out = adesioni_camera(righe, {"cgm4137": None, "cgm4138": "avs", "cgm4139": "pe"}, e)
    assert sorted((a.id_persona_esterno, a.partito, a.valido_dal, a.valido_al) for a in out) == [
        ("302080", "avs", date(2022, 10, 19), date(2022, 10, 27)),
        ("307436", "pe", date(2022, 10, 19), None),
    ]
    assert e.componenti_sconosciute == {"cgm9999"}
    assert all(a.fonte_url.startswith(CAM + "componenteGruppoMisto.rdf/") for a in out)


def test_camera_uri_inattesa():
    with pytest.raises(DatoInatteso):
        adesioni_camera([{"c": "x", "dep": "y", "ini": "20221019"}], {}, Esito())


def test_contenuto_coerente_con_i_partiti():
    conf = leggi("componenti-misto.yaml")
    slug = {p["slug"] for p in leggi("partiti.yaml")["partiti"]}
    for c in conf["camera"]["componenti"]:
        assert c["partito"] is None or c["partito"] in slug, c
    sen = adesioni_senato(conf["senato"])
    assert {a.partito for a in sen} <= slug
    assert all(a.fonte_url.startswith("https://www.senato.it/") for a in sen)
    assert all(a.valido_al is None or a.valido_al >= a.valido_dal for a in sen)
    # AVS al Senato: i senatori eletti con AVS sono nella componente del misto (issue #78)
    avs = {a.id_persona_esterno for a in sen if a.partito == "alleanza-verdi-e-sinistra"}
    assert avs >= {"22918", "36390", "36437"}
