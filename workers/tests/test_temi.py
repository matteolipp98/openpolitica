"""Tema delle promesse (#75): prompt, controllo della risposta, lotti fissi, tabella partito × tema."""

from uuid import uuid4

from op_workers.programmi import temi as te

VOCI = [
    te.Voce(uuid4(), "Salario minimo a 9 euro l'ora", "Introdurremo il salario minimo a 9 euro"),
    te.Voce(uuid4(), "Più soldi agli ospedali", "aumenteremo il fondo sanitario"),
    te.Voce(uuid4(), "Musei gratis la domenica", "musei gratuiti ogni domenica"),
]


def test_temi_ammessi_dal_file_piu_altro():
    assert te.ammessi() == ["economia", "welfare", "diritti", "ambiente", "istituzioni", "esteri", "altro"]
    assert te.schema()["items"]["properties"]["tema"]["enum"] == te.ammessi()


def test_prompt_con_temi_e_promesse_numerate():
    testo = te.prompt(VOCI)
    assert "[1] Salario minimo a 9 euro l'ora (dal testo: «Introdurremo il salario minimo a 9 euro»)" in testo
    assert "[3] Musei gratis" in testo
    assert '- "welfare": Sanità, scuola e famiglie.' in testo
    assert "{temi}" not in testo and "{promesse}" not in testo
    assert te.sha(testo) == te.sha(te.prompt(VOCI))  # stesso lotto, stessa impronta


def test_controllo_tiene_i_temi_validi_e_scarta_il_resto():
    risposta = [
        {"n": 1, "tema": "economia"},
        {"n": "2", "tema": "welfare"},  # numero come testo: va bene
        {"n": 1, "tema": "welfare"},  # ripetuto: vale il primo
        {"n": 3, "tema": "cultura"},  # tema che non esiste
        {"n": 4, "tema": "altro"},  # numero fuori dal lotto
        {"n": True, "tema": "altro"},
        "non è un oggetto",
    ]
    esito = te.controlla(risposta, VOCI)
    assert esito.temi == {VOCI[0].id: "economia", VOCI[1].id: "welfare"}
    assert len(esito.scartate) == 4
    assert te.controlla({"non": "un elenco"}, VOCI).temi == {}


def test_lotti_fissi():
    voci = [te.Voce(uuid4(), str(i), str(i)) for i in range(250)]
    assert [len(lo) for lo in te.lotti(voci, 100)] == [100, 100, 50]


def test_tabella_partito_per_tema():
    righe = [("lega", "economia", 3), ("lega", "altro", 1), ("pd", "esteri", 2), ("pd", None, 1)]
    t = te.tabella(righe).splitlines()
    assert t[0].startswith("| Partito | Lavoro, tasse e pensioni |")
    assert t[0].endswith("| Altro | Senza tema | Totale |")
    assert t[2] == "| lega | 3 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 4 |"
    assert t[3] == "| pd | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 1 | 3 |"
    assert "Senza tema" not in te.tabella(righe[:3])
