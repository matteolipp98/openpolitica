from op_workers.connettori import sonda_open_data as s


def test_semplifica_riduce_i_binding():
    b = [{"v": {"type": "uri", "value": "http://x/1"}, "n": {"type": "literal", "value": "3"}}]
    assert s.semplifica(b) == [{"v": "http://x/1", "n": "3"}]


def test_query_hanno_la_legislatura():
    for q in list(s.query_camera(19).values())[5:]:
        assert "19" in q or "UCASE" in q


def test_markdown_non_si_rompe_con_pipe_e_a_capo():
    r = {
        "eseguita_il": "ora",
        "legislatura": 19,
        "camera": {
            "x": {"nome": "x", "ok": True, "ms": 1, "righe": [{"a": "uno|due\ntre"}], "errore": None, "query": ""}
        },
        "senato": {},
        "altre_fonti": {},
    }
    md = s.in_markdown(r)
    assert "uno\\|due tre" in md
