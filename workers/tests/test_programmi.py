"""Programmi elettorali (#36): indirizzo dall'elenco del Ministero, divisione in paragrafi, testo illeggibile (#62)."""

import pytest

from op_workers.programmi.scarica import (
    Pagina,
    ProgrammaNonTrovato,
    leggibile,
    pagine,
    paragrafi,
    paragrafi_documento,
    url_programma,
)

ELENCO_URL = "https://dait.interno.gov.it/documenti/trasparenza/POLITICHE_20220925/POLITICHE_20220925.json"
STATUTO = {"tp_doc": 3, "desc_tp": "Statuto", "f_doc": "statuto.pdf"}


def _elenco(*contrassegni):
    return {"metadata": {}, "contrass": list(contrassegni)}


class TestUrlProgramma:
    def test_senza_fascicolo(self):
        e = _elenco(
            {"n_ord": 68, "l_fasc": None, "e_file": [STATUTO, {"tp_doc": 2, "f_doc": "(68_progr_2_)-programma.pdf"}]}
        )
        assert url_programma(e, ELENCO_URL, 68) == (
            "https://dait.interno.gov.it/documenti/trasparenza/POLITICHE_20220925/Documenti/68/"
            "%2868_progr_2_%29-programma.pdf"
        )

    def test_con_fascicolo_e_righe_doppie(self):
        # Il PD ha due righe: una con il programma (fascicolo A), una con il solo statuto
        e = _elenco(
            {"n_ord": 75, "l_fasc": "A", "e_file": [{"tp_doc": 2, "f_doc": "p.pdf"}, STATUTO]},
            {"n_ord": 75, "l_fasc": None, "e_file": [STATUTO]},
        )
        assert url_programma(e, ELENCO_URL, 75).endswith("/Documenti/75A/p.pdf")

    def test_stesso_programma_in_piu_fascicoli(self):
        # AVS: una riga per fascicolo, sempre lo stesso file
        righe = [{"n_ord": 65, "l_fasc": f, "e_file": [{"tp_doc": 2, "f_doc": "avs.pdf"}]} for f in (None, "A", "B")]
        assert url_programma(_elenco(*righe), ELENCO_URL, 65).endswith("/Documenti/65/avs.pdf")

    def test_programmi_diversi(self):
        righe = [{"n_ord": 1, "l_fasc": None, "e_file": [{"tp_doc": 2, "f_doc": f}]} for f in ("a.pdf", "b.pdf")]
        with pytest.raises(ProgrammaNonTrovato):
            url_programma(_elenco(*righe), ELENCO_URL, 1)

    def test_programma_mancante(self):
        with pytest.raises(ProgrammaNonTrovato):
            url_programma(_elenco({"n_ord": 71, "l_fasc": None, "e_file": [STATUTO]}), ELENCO_URL, 71)


RIGA = "Questa è una riga piena di testo che arriva fino al margine destro della pagina stampata"


class TestParagrafi:
    def test_unisce_le_righe_e_spezza_a_fine_frase_corta(self):
        testo = f"{RIGA}\n{RIGA}\nfine del primo paragrafo.\n{RIGA}\nfine del secondo."
        assert paragrafi(testo) == [f"{RIGA} {RIGA} fine del primo paragrafo.", f"{RIGA} fine del secondo."]

    def test_punti_elenco(self):
        testo = f"Le proposte:\n• ridurre le tasse sul lavoro\n• più asili nido\n{RIGA}"
        assert paragrafi(testo) == ["Le proposte:", "• ridurre le tasse sul lavoro", "• più asili nido", RIGA]

    def test_parola_spezzata_dal_trattino(self):
        assert paragrafi(f"{RIGA} e la sani-\ntà pubblica.") == [f"{RIGA} e la sanità pubblica."]

    def test_titolo_separato_dal_testo(self):
        testo = f"CASHBACK FISCALE\n{RIGA}\n{RIGA}"
        assert paragrafi(testo) == ["CASHBACK FISCALE", f"{RIGA} {RIGA}"]

    def test_riga_vuota(self):
        assert paragrafi(f"{RIGA}\n\n{RIGA}") == [RIGA, RIGA]


class TestParagrafiDocumento:
    def test_riunisce_il_paragrafo_che_continua_nella_pagina_dopo(self):
        lette = [Pagina(1, f"{RIGA}\n{RIGA} e", False), Pagina(2, f"continua qui.\n\n{RIGA}", True)]
        assert paragrafi_documento(lette) == [(1, f"{RIGA} {RIGA} e continua qui.", True), (2, RIGA, True)]

    def test_non_riunisce_dopo_un_punto(self):
        lette = [Pagina(1, f"{RIGA}.", False), Pagina(2, "minuscolo ma nuovo.", False)]
        assert [p for p, _, _ in paragrafi_documento(lette)] == [1, 2]


# Dal programma AVS 2022, pagina 5: la stessa pagina ha un pezzo letto bene e uno letto male da chi ha fatto il PDF
BUONO = (
    "Senza azione, da qui al 2050 i giorni di ondate di calore possono aumentare fino al 400%. I costi diretti "
    "del cambiamento climatico in Italia rischiano di raggiungere l'8% del PIL entro fine secolo, colpendo "
    "principalmente le fasce più fragili della popolazione, le infrastrutture, i terreni agricoli e il settore "
    "del turismo. L'adattamento deve diventare un investimento prioritario per evitare danni incalcolabili."
)
ILLEGGIBILE = (
    "L'Italia iientia tia le aiee piu colpitee si suriiscaldapiu velocemente della media globale Negli ultimi "
    "40 anni l'Italia ha registrato oltre 2Omila morti a causa di eventi estremi, seconda solo alla Francia; "
    "con il maggioi numeio di decessi Guaidando al futuio, i Italia iischi di diventare invivibile con "
    "tempelature estive che potrebbeio aumentale fino a 6 giadi le piecipitazioni estive diminuiie"
)


class TestLeggibile:
    def test_testo_buono(self):
        assert leggibile(BUONO)

    def test_accenti_persi_e_maiuscole(self):
        assert leggibile(BUONO.upper().replace("Ù", "U"))

    def test_testo_illeggibile(self):
        assert not leggibile(ILLEGGIBILE)

    def test_basta_un_pezzo_illeggibile_nella_pagina(self):
        assert not leggibile(f"{BUONO}\n{ILLEGGIBILE}\n{BUONO}")

    def test_testo_corto(self):
        assert leggibile("Programma elettorale")
        assert not leggibile("iientia tia aiee")


class TestPagine:
    def test_pagine_illeggibili_e_vuote_con_ocr(self, monkeypatch):
        import pdfplumber

        class Doc:
            pages = [type("P", (), {"extract_text": lambda self, t=t: t})() for t in (BUONO, ILLEGGIBILE, "")]

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

        monkeypatch.setattr(pdfplumber, "open", lambda _: Doc())
        lette = pagine(b"%PDF", ocr=lambda pdf, i: f"ocr {i}")
        assert lette == [Pagina(1, BUONO, False), Pagina(2, "ocr 1", True), Pagina(3, "ocr 2", True)]
