from op_workers.connettori import proponi_anagrafica as p


def test_etichetta_gruppo_con_parentesi_annidate():
    r = {
        "camera": {
            "gruppi_legislatura": {
                "righe": [
                    {
                        "g": "http://dati.camera.it/ocd/gruppoParlamentare.rdf/gr4152",
                        "nome": "NOI MODERATI (NOI CON L'ITALIA, CORAGGIO ITALIA, UDC E ITALIA AL CENTRO)"
                        "-MAIE-CENTRO POPOLARE "
                        "(NM(N-C-U-I)M-CP) (27.10.2022",
                        "sigla": "NM(N-C-U-I)M-CP",
                    }
                ]
            }
        }
    }
    [g] = p.gruppi_camera(r)
    assert g["id_esterno"] == "gr4152"
    assert g["valido_dal"] == "2022-10-27"
    assert g["nome"].startswith("NOI MODERATI")


def test_deputato_estrae_id_persona():
    r = {
        "camera": {
            "leader": {
                "righe": [
                    {
                        "d": "http://dati.camera.it/ocd/deputato.rdf/d308930_19",
                        "nome": "ELENA ETHEL",
                        "cognome": "SCHLEIN",
                    }
                ]
            }
        }
    }
    assert p.deputati(r)[0]["id"] == "308930"
