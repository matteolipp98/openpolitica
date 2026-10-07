"""Andamento nel tempo dai voti (ADR 0040; piano §3.13): "vota come il governo" e "il partito vota unito".

Si parte dai conteggi per gruppo (core.votazione_gruppo), senza nessun modello. Regole fisse:

- si guardano solo le votazioni finali non segrete;
- un partito conta su una votazione se almeno `membriMinimi` suoi parlamentari hanno votato
  (favorevoli + contrari + astenuti); i gruppi formati da più partiti non entrano (si attribuiscono per persona);
- vota_compatto: almeno 9 votanti su 10 hanno fatto la stessa scelta;
- vota_con_governo: la scelta prevalente del partito è uguale a quella prevalente della somma dei partiti
  al governo alla data; in caso di pari merito (del partito o del governo) la votazione non entra.

Il risultato ha lo stesso formato di apps/web/dati/esempio/andamento.json. Cambiare una regola richiede di
cambiare CALCOLO_VERSIONE: la serie si ricalcola sempre da capo, per tutto il periodo.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

CALCOLO_VERSIONE = "and-voti-1"
METRICHE = ("vota_con_governo", "vota_compatto")


@dataclass(frozen=True)
class VotoPartito:
    votazione_id: str
    data: date
    partito: str  # slug
    favorevoli: int
    contrari: int
    astenuti: int


def trimestre(d: date) -> str:
    return f"{d.year}-T{(d.month - 1) // 3 + 1}"


def trimestri_tra(dal: date, al: date) -> list[str]:
    out, a, t = [], dal.year, (dal.month - 1) // 3 + 1
    fine = (al.year, (al.month - 1) // 3 + 1)
    while (a, t) <= fine:
        out.append(f"{a}-T{t}")
        a, t = (a + 1, 1) if t == 4 else (a, t + 1)
    return out


def meta_trimestre(t: str) -> date:
    """Giorno di riferimento del trimestre per il ruolo (governo o no): il 15 del mese centrale."""
    return date(int(t[:4]), (int(t[-1]) - 1) * 3 + 2, 15)


def prevalente(fav: int, con: int, ast: int) -> str | None:
    """La scelta con più voti; None se c'è un pari merito in testa o nessun voto."""
    conti = {"favorevole": fav, "contrario": con, "astenuto": ast}
    massimo = max(conti.values())
    primi = [k for k, v in conti.items() if v == massimo]
    return primi[0] if massimo > 0 and len(primi) == 1 else None


def unito(fav: int, con: int, ast: int) -> bool:
    votanti = fav + con + ast
    return votanti > 0 and 10 * max(fav, con, ast) >= 9 * votanti


def calcola(
    voti: Iterable[VotoPartito],
    al_governo: Callable[[str, date], bool],
    membri_minimi: int,
) -> dict:
    """Serie per partito e trimestre: {trimestri, governo, serie, calcolo_versione}."""
    per_votazione: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    data_di: dict[str, date] = {}
    for v in voti:
        c = per_votazione[v.votazione_id][v.partito]
        c[0] += v.favorevoli
        c[1] += v.contrari
        c[2] += v.astenuti
        data_di[v.votazione_id] = v.data
    if not data_di:
        return {"trimestri": [], "governo": {}, "serie": {}, "calcolo_versione": CALCOLO_VERSIONE}

    trimestri = trimestri_tra(min(data_di.values()), max(data_di.values()))
    indice = {t: i for i, t in enumerate(trimestri)}
    partiti = sorted({p for conti in per_votazione.values() for p in conti})
    serie = {p: {m: [{"n": 0, "d": 0} for _ in trimestri] for m in METRICHE} for p in partiti}

    for vid, conti in per_votazione.items():
        quando = data_di[vid]
        i = indice[trimestre(quando)]
        governo = [0, 0, 0]
        for p, c in conti.items():
            if al_governo(p, quando):
                governo = [a + b for a, b in zip(governo, c, strict=True)]
        scelta_governo = prevalente(*governo)
        for p, (fav, con, ast) in conti.items():
            if fav + con + ast < membri_minimi:
                continue
            u = serie[p]["vota_compatto"][i]
            u["d"] += 1
            u["n"] += unito(fav, con, ast)
            scelta = prevalente(fav, con, ast)
            if scelta and scelta_governo:
                g = serie[p]["vota_con_governo"][i]
                g["d"] += 1
                g["n"] += scelta == scelta_governo

    return {
        "trimestri": trimestri,
        "governo": {p: [al_governo(p, meta_trimestre(t)) for t in trimestri] for p in partiti},
        "serie": serie,
        "calcolo_versione": CALCOLO_VERSIONE,
    }


def ruoli_da_righe(righe: Iterable[tuple[str, str, date, date | None]]) -> Callable[[str, date], bool]:
    """Da (slug, ruolo, valido_dal, valido_al) a una funzione "al governo alla data"."""
    periodi: dict[str, list[tuple[date, date | None]]] = defaultdict(list)
    for slug, ruolo, dal, al in righe:
        if ruolo == "governo":
            periodi[slug].append((dal, al))

    def al_governo(slug: str, quando: date) -> bool:
        return any(dal <= quando and (al is None or quando <= al) for dal, al in periodi.get(slug, ()))

    return al_governo


# Un gruppo conta per un partito solo se in quella data è collegato a quel solo partito.
QUERY_VOTI = """
select v.id::text, v.data, p.slug, vg.favorevoli, vg.contrari, vg.astenuti
from core.votazione v
join core.votazione_gruppo vg on vg.votazione_id = v.id
join core.gruppo_partito gp on gp.gruppo_id = vg.gruppo_id
  and v.data >= gp.valido_dal and (gp.valido_al is null or v.data <= gp.valido_al)
join core.partito p on p.id = gp.partito_id
where v.finale and not v.segreta and v.legislatura = %(legislatura)s
  and (select count(*) from core.gruppo_partito g2
       where g2.gruppo_id = vg.gruppo_id
         and v.data >= g2.valido_dal and (g2.valido_al is null or v.data <= g2.valido_al)) = 1
"""
QUERY_RUOLI = """
select p.slug, r.ruolo, r.valido_dal, r.valido_al
from core.partito_ruolo r join core.partito p on p.id = r.partito_id
"""


def da_database(conn, legislatura: int, membri_minimi: int) -> dict:
    with conn.cursor() as cur:
        cur.execute(QUERY_RUOLI)
        al_governo = ruoli_da_righe(cur.fetchall())
        cur.execute(QUERY_VOTI, {"legislatura": legislatura})
        voti = [VotoPartito(*r) for r in cur.fetchall()]
    return calcola(voti, al_governo, membri_minimi)


def riassunto(andamento: dict) -> str:
    """Poche righe leggibili per il sommario del workflow."""
    righe = [f"Andamento dai voti ({andamento['calcolo_versione']}): {len(andamento['trimestri'])} trimestri"]
    for p, s in andamento["serie"].items():
        g = s["vota_con_governo"]
        u = s["vota_compatto"]
        n_g, d_g = sum(x["n"] for x in g), sum(x["d"] for x in g)
        n_u, d_u = sum(x["n"] for x in u), sum(x["d"] for x in u)
        righe.append(f"- {p}: come il governo {n_g} su {d_g}, unito {n_u} su {d_u}")
    return "\n".join(righe)


def main(argv: list[str] | None = None) -> int:
    import psycopg
    import yaml

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--uscita", type=Path, help="file JSON da scrivere (altrimenti stampa solo il riassunto)")
    a = ap.parse_args(argv)
    radice = Path(__file__).resolve().parents[3]
    parametri = yaml.safe_load((radice / "content" / "parametri.yaml").read_text(encoding="utf8"))["posizioni"]
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        andamento = da_database(conn, int(parametri["legislaturaRiferimento"]), int(parametri["membriMinimi"]))
    if a.uscita:
        a.uscita.parent.mkdir(parents=True, exist_ok=True)
        a.uscita.write_text(json.dumps(andamento, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    print(riassunto(andamento))
    return 0


if __name__ == "__main__":
    sys.exit(main())
