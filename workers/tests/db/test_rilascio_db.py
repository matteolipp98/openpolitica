from decimal import Decimal

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
