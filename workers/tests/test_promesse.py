"""Estrazione delle promesse (#37): controllo della citazione, scarti, lotti, con un Gemini finto."""

import json

import httpx
import pytest

from op_workers.catalogo.gemini import Gemini
from op_workers.programmi import promesse as pr

LOTTO = [
    (1, "Il nostro programma per l’Italia."),
    (2, "Introdurremo il salario minimo a 9 euro l'ora entro il 2023, per tutti i lavoratori dipendenti."),
    (3, "Vogliamo una scuola più giusta: aumenteremo gli stipendi degli inse-"),
    (4, "gnanti — con fondi europei — e ridurremo le classi “pollaio”."),
]


@pytest.mark.parametrize(
    ("citazione", "atteso"),
    [
        ("Introdurremo il salario minimo a 9 euro l’ora entro il 2023", (2, 2)),  # apostrofo diverso
        ("  «introdurremo   il salario minimo a 9 euro l'ora»  ", (2, 2)),  # spazi, virgolette, maiuscola
        ('con fondi europei - e ridurremo le classi "pollaio"', (4, 4)),  # trattino e virgolette diversi
        ("aumenteremo gli stipendi degli inse- gnanti", (3, 4)),  # passa da un paragrafo all'altro
        ("Introdurremo il salario minimo a 10 euro l'ora", None),  # numero cambiato
        ("Introdurremo il salario minimo ... entro il 2023", None),  # puntini per saltare parti
        ("salario minimo", None),  # troppo corta per ritrovarla
    ],
)
def test_citazione_cercata_letteralmente(citazione, atteso):
    assert pr.trova(citazione, LOTTO) == atteso


def test_controllo_tiene_le_trovate_e_conta_le_scartate():
    risposta = [
        {"citazione": "Introdurremo il salario minimo a 9 euro l'ora entro il 2023", "misura": "Salario minimo",
         "orizzonte": "entro il 2023", "beneficiari": "", "livello_competenza": "nazionale"},
        {"citazione": "Introdurremo il salario minimo a 9 euro l'ora entro il 2023", "misura": "Salario minimo"},
        {"citazione": "Aboliremo il canone della televisione", "misura": "Niente canone"},
        {"citazione": "ridurremo le classi “pollaio”", "misura": "", "livello_competenza": "non_chiaro"},
        "non è un oggetto",
    ]  # fmt: skip
    esito = pr.controlla(risposta, LOTTO)
    assert len(esito.promesse) == 1  # la seconda è un doppione della prima
    p = esito.promesse[0]
    assert (p.paragrafo_da, p.paragrafo_a, p.orizzonte, p.beneficiari, p.livello_competenza) == (
        2, 2, "entro il 2023", None, "nazionale")  # fmt: skip
    assert [s["motivo"] for s in esito.scartate] == ["citazione non trovata", "misura vuota", "non è un oggetto"]
    assert pr.controlla({"non": "un elenco"}, LOTTO).promesse == []


def test_lotti_per_lunghezza():
    par = [(i, "x" * 400) for i in range(1, 11)]
    assert [[n for n, _ in lo] for lo in pr.lotti(par, 1000)] == [[1, 2], [3, 4], [5, 6], [7, 8], [9, 10]]
    assert [len(lo) for lo in pr.lotti([(1, "x" * 5000), (2, "y")], 1000)] == [1, 1]


def test_prompt_versionato_con_i_paragrafi_numerati():
    testo = pr.prompt(LOTTO[:2])
    assert "[2] Introdurremo il salario minimo" in testo
    assert "{paragrafi}" not in testo
    assert pr.sha(testo) == pr.sha(pr.prompt(LOTTO[:2]))  # stesso lotto, stessa impronta: niente seconda chiamata


def gemini_finto(risposte: list, chiamate: list, **kw) -> Gemini:
    """Gemini con trasporto finto: restituisce in ordine le risposte date."""

    def gestore(req):
        chiamate.append(json.loads(req.content))
        dati = risposte[len(chiamate) - 1]
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": json.dumps(dati)}]}}], "modelVersion": "finto-001"},
        )

    return Gemini(chiave="k", modello="finto", client=httpx.Client(transport=httpx.MockTransport(gestore)), pausa=0,
                  **kw)  # fmt: skip


def test_lo_schema_va_al_modello():
    chiamate = []
    g = gemini_finto([[]], chiamate)
    g.json(pr.prompt(LOTTO), pr.SCHEMA)
    conf = chiamate[0]["generationConfig"]
    assert conf["responseMimeType"] == "application/json"
    assert conf["responseSchema"]["items"]["required"] == ["citazione", "misura"]
