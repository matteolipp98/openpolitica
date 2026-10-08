import json
from datetime import date
from decimal import Decimal

import httpx

from op_workers.catalogo.gemini import Gemini
from op_workers.posizioni.da_voti import Parametri
from op_workers.rilascio.crea import costruisci, posizioni

P = Parametri(Decimal("0.5"), 3, 19)


def _prepara(c):
    pa = c.execute("insert into core.partito (slug, nome) values ('aa', 'A') returning id").fetchone()[0]
    g = c.execute(
        "insert into core.gruppo_parlamentare (ramo, legislatura, id_esterno) values ('camera', 19, 'g1') returning id"
    ).fetchone()[0]
    c.execute(
        "insert into core.gruppo_partito (gruppo_id, partito_id, valido_dal) values (%s, %s, '2022-10-13')", (g, pa)
    )
    v = c.execute(
        """insert into core.votazione
             (ramo, legislatura, id_esterno, data, finale, favorevoli, contrari, astenuti, url, atto_titolo)
           values ('camera', 19, 'vs1', '2023-05-11', true, 0, 0, 0, 'https://example.org/vs1', 'Salario minimo')
           returning id"""
    ).fetchone()[0]
    c.execute(
        "insert into core.votazione_gruppo (votazione_id, gruppo_id, favorevoli, contrari) values (%s, %s, 2, 20)",
        (v, g),
    )
    pe = c.execute("insert into core.persona (slug, nome, cognome) values ('mr', 'M', 'R') returning id").fetchone()[0]
    c.execute("insert into core.voto (votazione_id, persona_id, espressione) values (%s, %s, 'favorevole')", (v, pe))


CATALOGO = {
    "enunciati": [
        {"id": "e-1", "stato": "attivo",
         "origine": {"votazione": {"ramo": "camera", "legislatura": 19, "idEsterno": "vs1"}, "direzione": -1}},
        {"id": "e-2", "stato": "attivo",
         "origine": {"votazione": {"ramo": "camera", "legislatura": 19, "idEsterno": "non-esiste"}, "direzione": 1}},
    ]
}  # fmt: skip


def test_posizioni_dai_voti(conn):
    _prepara(conn)
    sogg = [{"id": "aa", "tipo": "partito"}, {"id": "mr", "tipo": "persona"}, {"id": "zz", "tipo": "partito"}]
    pos = posizioni(conn, CATALOGO, sogg, P)
    # il partito ha votato contro; l'enunciato ha direzione -1, quindi è d'accordo con l'enunciato
    assert pos["aa"]["e-1"]["valore"] == 2
    assert pos["aa"]["e-1"]["evidenze"][0] == {
        "testo": "Ha votato contro: Salario minimo",
        "quando": "Camera, 11 maggio 2023",
        "url": "https://example.org/vs1",
    }
    assert pos["mr"]["e-1"]["valore"] == -2
    assert pos["zz"]["e-1"] == {"valore": None, "stato": "non_documentata", "evidenze": []}
    assert pos["aa"]["e-2"]["stato"] == "non_documentata"


def test_costruisci_senza_catalogo(conn):
    _prepara(conn)
    file = costruisci(conn)
    m = file["manifest.json"]
    assert m["esempio"] is False and m["sezioni"]["posizioni"] is (len(file["domande.json"]) > 0)
    assert m["fonti"]["camera"]["ultima_votazione"] == "2023-05-11"
    assert any(s["tipo"] == "persona" for s in file["soggetti.json"])


def test_correzioni_nel_pacchetto(conn):
    _prepara(conn)
    conn.execute(
        """insert into core.correzione (oggetto_tipo, oggetto_id, prima, dopo, motivazione)
           values ('posizione', 'aa:e-1', '{"testo": "A favore"}', '{"testo": "Contro"}', 'Voto letto al contrario')"""
    )
    c = costruisci(conn)["correzioni.json"]
    assert c[0]["prima"] == "A favore" and c[0]["dopo"] == "Contro" and c[0]["motivo"] == "Voto letto al contrario"


# ---------- home (#76): seggi, programmi ----------


def _gruppo(c, ramo, sigla, partito=None):
    g = c.execute(
        "insert into core.gruppo_parlamentare (ramo, legislatura, id_esterno) values (%s, 19, %s) returning id",
        (ramo, sigla),
    ).fetchone()[0]
    if partito:
        c.execute(
            """insert into core.gruppo_partito (gruppo_id, partito_id, valido_dal)
               select %s, id, '2022-10-13' from core.partito where slug = %s""",
            (g, partito),
        )
    return g


def _parlamentare(c, slug, gruppo, dal="2022-10-13", al=None, partito=None):
    pe = c.execute(
        "insert into core.persona (slug, nome, cognome) values (%s, 'N', 'C') returning id", (slug,)
    ).fetchone()[0]
    c.execute(
        """insert into core.appartenenza (persona_id, tipo, gruppo_id, valido_dal, valido_al)
           values (%s, 'gruppo', %s, %s, %s)""",
        (pe, gruppo, dal, al),
    )
    if partito:
        c.execute(
            """insert into core.appartenenza (persona_id, tipo, partito_id, valido_dal)
               select %s, 'partito', id, '2022-10-13' from core.partito where slug = %s""",
            (pe, partito),
        )
    return pe


def test_parlamento_seggi_alla_data(conn):
    from op_workers.rilascio.crea import parlamento

    for s in ("aa", "bb", "cc"):
        conn.execute("insert into core.partito (slug, nome) values (%s, %s)", (s, s.upper()))
    ga, misto, gc = (
        _gruppo(conn, "camera", "ga", "aa"),
        _gruppo(conn, "camera", "misto"),
        _gruppo(conn, "senato", "gc", "cc"),
    )
    _parlamentare(conn, "p1", ga)
    _parlamentare(conn, "p2", ga)
    _parlamentare(conn, "p3", ga, al="2024-01-01")  # non è più deputato
    _parlamentare(conn, "p4", misto, partito="bb")  # nel misto, ma iscritto a un partito seguito
    _parlamentare(conn, "p5", misto)  # nel misto senza partito
    _parlamentare(conn, "p6", gc)  # in un partito che non seguiamo
    p7 = _parlamentare(conn, "p7", ga, al="2025-03-01")  # cambia gruppo: conta una volta sola, nel gruppo nuovo
    conn.execute(
        """insert into core.appartenenza (persona_id, tipo, gruppo_id, valido_dal)
           values (%s, 'gruppo', %s, '2025-03-01')""",
        (p7, misto),
    )

    out = parlamento(conn, ["aa", "bb"], 19, date(2026, 10, 8))
    assert out == {
        "data": "2026-10-08",
        "rami": {
            "camera": {"totale": 5, "partiti": {"aa": 2, "bb": 1}, "altri": 2},
            "senato": {"totale": 1, "partiti": {"aa": 0, "bb": 0}, "altri": 1},
        },
    }


TESTO = "Introdurremo il salario minimo a 9 euro l'ora entro il 2023.\n\nAboliremo il superbollo sulle auto."
PROMESSE = [
    {"citazione": "Introdurremo il salario minimo a 9 euro l'ora", "misura": "Salario minimo di 9 euro l'ora",
     "orizzonte": "entro il 2023"},
    {"citazione": "Aboliremo il superbollo sulle auto", "misura": "Niente superbollo"},
]  # fmt: skip


def gemini_finto(risposte: list) -> Gemini:
    """Gemini con trasporto finto: restituisce in ordine le risposte date."""
    chiamate = []

    def gestore(req):
        chiamate.append(req)
        testo = json.dumps(risposte[len(chiamate) - 1])
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": testo}]}}],
                                         "modelVersion": "finto-001"})  # fmt: skip

    return Gemini(chiave="k", modello="finto", client=httpx.Client(transport=httpx.MockTransport(gestore)), pausa=0)


def test_programmi_temi_precise_e_comune(conn):
    from op_workers.programmi import promesse as pr
    from op_workers.programmi import temi as te
    from op_workers.programmi.scarica import Pagina, collega, salva_documento
    from op_workers.rilascio.crea import programmi

    for s in ("azione", "italia-viva", "lega", "pd"):
        conn.execute("insert into core.partito (slug, nome) values (%s, %s)", (s, s))
    # Azione e Italia Viva: lo stesso file; la Lega: un file diverso con lo stesso testo e una copertina
    salva_documento(conn, url="https://example.org/a.pdf", data=date(2022, 9, 25), sha256="c" * 64,
                    lette=[Pagina(1, TESTO, False)])  # fmt: skip
    collega(conn, partiti=["azione", "italia-viva"], elezione=date(2022, 9, 25), sha256="c" * 64)
    salva_documento(conn, url="https://example.org/l.pdf", data=date(2022, 9, 25), sha256="d" * 64,
                    lette=[Pagina(1, "Programma della Lega.\n\n" + TESTO, False)])  # fmt: skip
    collega(conn, partiti=["lega"], elezione=date(2022, 9, 25), sha256="d" * 64)
    # alla Lega diamo solo la prima promessa: due lotti di temi identici nello stesso giro non si possono salvare
    # (i documenti si leggono in ordine di partito: prima quello di Azione)
    pr.esegui(conn, gemini_finto([PROMESSE, PROMESSE[:1]]))
    temi = [{"n": 1, "tema": "economia"}, {"n": 2, "tema": "altro"}]
    te.esegui(conn, gemini_finto([temi, temi]))

    out = programmi(conn, ["azione", "italia-viva", "lega", "pd"])
    assert set(out) == {"azione", "italia-viva", "lega"}  # il PD non ha un programma
    assert out["azione"] == {
        "elezione": "2022-09-25",
        "promesse": 2,
        "precise": {"n": 1, "d": 2},  # 9 euro entro il 2023; il superbollo non ha né quanto né quando
        "temi": {"altro": 1, "economia": 1},
        "comune": {"stesso_documento": ["italia-viva"], "testo_uguale": ["lega"]},
    }
    assert out["lega"]["promesse"] == 1 and out["lega"]["temi"] == {"economia": 1}
    assert out["lega"]["comune"] == {"stesso_documento": [], "testo_uguale": ["azione", "italia-viva"]}
