from op_workers.andamento.da_voti import da_database


def _partito(c, slug, ruolo):
    pid = c.execute("insert into core.partito (slug, nome) values (%s, %s) returning id", (slug, slug)).fetchone()[0]
    c.execute(
        "insert into core.partito_ruolo (partito_id, ruolo, valido_dal) values (%s, %s, '2022-10-13')", (pid, ruolo)
    )
    return pid


def _gruppo(c, ide, *partiti):
    gid = c.execute(
        "insert into core.gruppo_parlamentare (ramo, legislatura, id_esterno) values ('camera', 19, %s) returning id",
        (ide,),
    ).fetchone()[0]
    for p in partiti:
        c.execute(
            "insert into core.gruppo_partito (gruppo_id, partito_id, valido_dal) values (%s, %s, '2022-10-13')",
            (gid, p),
        )
    return gid


def _votazione(c, ide, data, finale=True, segreta=False):
    return c.execute(
        """insert into core.votazione
             (ramo, legislatura, id_esterno, data, finale, segreta, favorevoli, contrari, astenuti, url)
           values ('camera', 19, %s, %s, %s, %s, 0, 0, 0, 'https://example.org') returning id""",
        (ide, data, finale, segreta),
    ).fetchone()[0]


def test_da_database(conn):
    c = conn
    a, b, x = _partito(c, "aa", "governo"), _partito(c, "bb", "opposizione"), _partito(c, "xx", "opposizione")
    ga, gb, gmisto = _gruppo(c, "g1", a), _gruppo(c, "g2", b), _gruppo(c, "g3", b, x)  # g3: gruppo di due partiti
    for ide, finale, segreta in [("v1", True, False), ("v2", False, False), ("v3", True, True)]:
        vid = _votazione(c, ide, "2023-02-01", finale, segreta)
        for g, fav, con in [(ga, 20, 0), (gb, 0, 20), (gmisto, 20, 0)]:
            c.execute(
                """insert into core.votazione_gruppo (votazione_id, gruppo_id, favorevoli, contrari)
                   values (%s, %s, %s, %s)""",
                (vid, g, fav, con),
            )
    r = da_database(c, 19, 3)
    # solo v1 (finale, non segreta); il gruppo di due partiti non entra
    assert r["serie"]["bb"]["vota_con_governo"] == [{"n": 0, "d": 1}]
    assert r["serie"]["aa"]["vota_compatto"] == [{"n": 1, "d": 1}]
    assert "xx" not in r["serie"]


def test_azione_alla_camera_con_i_gruppi_dei_voti(conn):
    """Issue #79: dopo la divisione del 20.11.2023 i voti di Azione alla Camera portano il gruppo gr4212, non
    gr4135 delle adesioni. Con l'anagrafica vera di content/ quei voti vanno ad Azione."""
    from op_workers.anagrafica.sincronizza import sincronizza

    c = conn
    sincronizza(c)
    gid = {
        ide: c.execute(
            "select id from core.gruppo_parlamentare where ramo = 'camera' and legislatura = 19 and id_esterno = %s",
            (ide,),
        ).fetchone()[0]
        for ide in ("gr4133", "gr4212", "gr4153", "gr4291")
    }
    vid = _votazione(c, "vs-azione", "2024-02-01")
    for ide, fav, con in [("gr4133", 100, 0), ("gr4212", 0, 9), ("gr4153", 7, 0), ("gr4291", 0, 0)]:
        c.execute(
            "insert into core.votazione_gruppo (votazione_id, gruppo_id, favorevoli, contrari) values (%s, %s, %s, %s)",
            (vid, gid[ide], fav, con),
        )
    r = da_database(c, 19, 3)
    assert r["serie"]["azione"]["vota_con_governo"] == [{"n": 0, "d": 1}]
    assert r["serie"]["noi-moderati"]["vota_con_governo"] == [{"n": 1, "d": 1}]
    assert "italia-viva" not in r["serie"]  # gr4291 vale solo dal 16.6.2026
