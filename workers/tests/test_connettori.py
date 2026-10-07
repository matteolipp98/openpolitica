"""Test dei connettori su righe con la forma reale vista nella sonda del 2026-10-07."""

from datetime import date

import httpx
import pytest

from op_workers.comuni.sparql import ClientSparql, ErroreSparql
from op_workers.connettori import camera, senato
from op_workers.connettori.base import DatoInatteso

CAM = "http://dati.camera.it/ocd/"
SEN = "http://dati.senato.it/"


class SparqlFinto:
    """Restituisce righe prefissate; registra le query per controllarle."""

    def __init__(self, righe):
        self.righe, self.query = righe, []

    def pagine(self, query, pagina=5000):
        self.query.append(query)
        return list(self.righe)


class TestCamera:
    VOTAZIONE = {
        "v": CAM + "votazione.rdf/vs19_718_024",
        "data": "20261001",
        "tipo": "Finale atto Camera",
        "titolo": "Votazione finale ",
        "descr": "DDL 3118 - VOTO FINALE",
        "finale": "1",
        "fiducia": "0",
        "segreta": "0",
        "fav": "178",
        "con": "57",
        "ast": "79",
        "approvato": "1",
        "url": "http://documenti.camera.it/apps/votazioni/votazionitutte/schedavotazione.asp?Legislatura=XIX",
    }

    def test_votazione_normalizzata(self):
        v = camera.normalizza_votazione(self.VOTAZIONE, 19)
        assert (v.id_esterno, v.data, v.finale, v.approvata) == ("vs19_718_024", date(2026, 10, 1), True, True)
        assert (v.favorevoli, v.contrari, v.astenuti) == (178, 57, 79)
        assert v.atto_ref == "C.3118"  # dalla descrizione: l'URI dell'atto manca nelle votazioni recenti
        assert v.titolo == "Votazione finale"

    def test_atto_dall_uri_ha_precedenza(self):
        r = {**self.VOTAZIONE, "atto": CAM + "attocamera.rdf/ac19_3045"}
        assert camera.normalizza_votazione(r, 19).atto_ref == "C.3045"

    def test_duplicati_del_dataset_scartati(self):
        finto = SparqlFinto([self.VOTAZIONE, dict(self.VOTAZIONE)])
        assert len(list(camera.ConnettoreCamera(finto).votazioni(19, date(2026, 1, 1)))) == 1
        assert 'FILTER(STR(?data) >= "20260101")' in finto.query[0]
        assert "DISTINCT" in finto.query[0]

    @pytest.mark.parametrize(
        ("tipo", "descr", "atteso"),
        [
            ("Favorevole", None, "favorevole"),
            ("Contrario", "", "contrario"),
            ("Astensione", None, "astenuto"),
            ("Non ha votato", "Non ha partecipato", "assente"),
            ("Non ha votato", "In missione", "in_missione"),
            ("Non ha votato", "Presidente di turno", "presidente"),
        ],
    )
    def test_espressioni(self, tipo, descr, atteso):
        assert camera.espressione(tipo, descr) == atteso

    def test_espressione_sconosciuta_ferma_l_import(self):
        with pytest.raises(DatoInatteso):
            camera.espressione("Voto segreto", None)

    def test_voto(self):
        v = camera.normalizza_voto(
            {
                "x": CAM + "voto.rdf/v19_718011_302103",
                "v": CAM + "votazione.rdf/vs19_718_011",
                "dep": CAM + "deputato.rdf/d302103_19",
                "tipo": "Contrario",
                "gruppo": CAM + "gruppoParlamentare.rdf/gr4133",
            }
        )
        assert (v.id_votazione_esterno, v.id_persona_esterno, v.espressione, v.id_gruppo_esterno) == (
            "vs19_718_011",
            "302103",
            "contrario",
            "gr4133",
        )

    def test_data_non_valida(self):
        with pytest.raises(DatoInatteso):
            camera.data_camera("2026-10-01")


class TestSenato:
    VOTAZIONE = {
        "v": SEN + "votazione/19-167-42",
        "data": "2024-03-12",
        "label": "Votazione finale",
        "fav": "86",
        "con": "49",
        "esito": "Approvato",
        "titolo": "Conversione in legge, con modificazioni, del decreto-legge 19 gennaio 2024, n. 5",
        "fase": "S.1056",
    }

    def test_votazione_normalizzata(self):
        v = senato.normalizza_votazione(self.VOTAZIONE, 19)
        assert (v.id_esterno, v.data, v.finale, v.atto_ref, v.approvata) == (
            "19-167-42",
            date(2024, 3, 12),
            True,
            "S.1056",
            True,
        )
        assert v.astenuti == 0

    def test_archi_diventano_un_voto_per_senatore(self):
        v = SEN + "votazione/19-167-42"
        righe = [
            {"v": v, "p": senato.OSR + "favorevole", "sen": SEN + "senatore/3900"},
            {"v": v, "p": senato.OSR + "contrario", "sen": SEN + "senatore/30742"},
            {"v": v, "p": senato.OSR + "presenteNonVotante", "sen": SEN + "senatore/25407"},
            {"v": v, "p": senato.OSR + "inCongedoMissione", "sen": SEN + "senatore/30110"},
            {"v": v, "p": senato.OSR + "presidente", "sen": SEN + "senatore/1"},
            {"v": v, "p": senato.OSR + "presenteNonVotante", "sen": SEN + "senatore/1"},
        ]
        voti = {x.id_persona_esterno: x.espressione for x in senato.voti_da_archi(righe)}
        assert voti == {
            "3900": "favorevole",
            "30742": "contrario",
            "25407": "non_votante",
            "30110": "in_missione",
            "1": "presidente",
        }

    def test_voti_contraddittori_fermano_l_import(self):
        v = SEN + "votazione/19-1-1"
        righe = [
            {"v": v, "p": senato.OSR + "favorevole", "sen": SEN + "senatore/1"},
            {"v": v, "p": senato.OSR + "contrario", "sen": SEN + "senatore/1"},
        ]
        with pytest.raises(DatoInatteso):
            senato.voti_da_archi(righe)

    def test_query_senza_values(self):
        assert "VALUES" not in senato.query_voti_del_giorno(date(2024, 3, 12))
        assert "VALUES" not in senato.query_votazioni(19, date(2022, 10, 13))

    def test_voti_di_altre_legislature_esclusi(self):
        righe = [{"v": SEN + "votazione/18-1-1", "p": senato.OSR + "favorevole", "sen": SEN + "senatore/1"}]
        assert list(senato.ConnettoreSenato(SparqlFinto(righe)).voti_del_giorno(19, date(2022, 10, 1))) == []


class TestClientSparql:
    def _client(self, gestore):
        return ClientSparql("https://esempio.it/sparql", httpx.Client(transport=httpx.MockTransport(gestore)), attesa=0)

    def test_riprova_sugli_errori_temporanei(self):
        chiamate = []

        def gestore(req):
            chiamate.append(req)
            if len(chiamate) < 3:
                return httpx.Response(503)
            return httpx.Response(200, json={"results": {"bindings": [{"x": {"type": "literal", "value": "1"}}]}})

        assert self._client(gestore).select("SELECT ?x WHERE {}") == [{"x": "1"}]
        assert len(chiamate) == 3

    def test_errore_400_non_si_riprova(self):
        chiamate = []

        def gestore(req):
            chiamate.append(req)
            return httpx.Response(400)

        with pytest.raises(ErroreSparql):
            self._client(gestore).select("SELECT ?x WHERE {}")
        assert len(chiamate) == 1

    def test_paginazione(self):
        def gestore(req):
            offset = int(req.url.params["query"].rsplit("OFFSET ", 1)[1])
            n = 2 if offset < 4 else 1
            righe = [{"x": {"value": str(offset + i)}} for i in range(n)]
            return httpx.Response(200, json={"results": {"bindings": righe}})

        righe = self._client(gestore).pagine("SELECT ?x WHERE {} ORDER BY ?x", pagina=2)
        assert [r["x"] for r in righe] == ["0", "1", "2", "3", "4"]
