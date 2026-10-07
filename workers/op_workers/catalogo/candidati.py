"""Votazioni candidate a diventare domande (ADR 0030, passi 1-2): solo dati, nessun modello."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

import psycopg

from op_workers.posizioni.da_voti import Parametri, orientamento_da_conteggi

QUERY = """
with gruppo_partito_alla_data as (
  select v.id as votazione_id, vg.gruppo_id, min(gp.partito_id::text) as partito_id, count(*) as partiti
  from core.votazione v
  join core.votazione_gruppo vg on vg.votazione_id = v.id
  join core.gruppo_partito gp on gp.gruppo_id = vg.gruppo_id
       and v.data >= gp.valido_dal and (gp.valido_al is null or v.data <= gp.valido_al)
  where v.legislatura = %(leg)s
  group by v.id, vg.gruppo_id
)
select v.id::text, v.ramo, v.id_esterno, v.data, v.atto_ref, v.atto_titolo, v.descrizione, v.approvata,
       v.favorevoli, v.contrari, v.astenuti, p.slug,
       sum(vg.favorevoli)::int, sum(vg.contrari)::int, sum(vg.astenuti)::int
from core.votazione v
join gruppo_partito_alla_data g on g.votazione_id = v.id and g.partiti = 1   -- gruppi di un solo partito
join core.votazione_gruppo vg on vg.votazione_id = v.id and vg.gruppo_id = g.gruppo_id
join core.partito p on p.id = g.partito_id::uuid
where v.legislatura = %(leg)s and v.finale and v.coerente and not v.fiducia and not v.segreta
  and v.atto_titolo is not null
group by v.id, p.slug
order by v.data, v.id
"""


@dataclass
class Candidata:
    votazione_id: str
    ramo: str
    id_esterno: str
    data: date
    atto_ref: str | None
    atto_titolo: str
    approvata: bool | None
    favorevoli: int
    contrari: int
    astenuti: int
    orientamenti: dict[str, int] = field(default_factory=dict)  # partito → -1/0/+1

    @property
    def minoranza(self) -> float:
        espressi = self.favorevoli + self.contrari
        return min(self.favorevoli, self.contrari) / espressi if espressi else 0.0

    @property
    def chiave_atto(self) -> str:
        """Stessa legge votata alla Camera e al Senato: una sola domanda (ADR 0030, mai due dallo stesso atto)."""
        return re.sub(r"\W+", " ", self.atto_titolo.lower()).strip()[:160]


def candidate(
    conn: psycopg.Connection, leg: int, perimetro: set[str], p: Parametri, minoranza_minima: float
) -> tuple[list[Candidata], dict[str, int]]:
    """Restituisce le candidate e il conteggio degli scarti per motivo (per il rapporto pubblico)."""
    per_votazione: dict[str, Candidata] = {}
    for vid, ramo, ide, data, atto_ref, atto_tit, _descr, appr, fav, con, ast, partito, pf, pc, pa in conn.execute(
        QUERY, {"leg": leg}
    ):
        c = per_votazione.setdefault(vid, Candidata(vid, ramo, ide, data, atto_ref, atto_tit, appr, fav, con, ast))
        if partito in perimetro:
            o = orientamento_da_conteggi(pf, pc, pa, p)
            if o is not None:
                c.orientamenti[partito] = o

    scarti: dict[str, int] = defaultdict(int)
    tenute: dict[str, Candidata] = {}
    for c in per_votazione.values():
        if c.minoranza < minoranza_minima:
            scarti["poco divisiva (quasi tutti d'accordo)"] += 1
            continue
        lati = set(c.orientamenti.values())
        if not {1, -1} <= lati:
            scarti["nessun partito seguito a favore e uno contro"] += 1
            continue
        precedente = tenute.get(c.chiave_atto)
        if precedente and precedente.data >= c.data:
            scarti["stessa legge già votata nell'altro ramo"] += 1
            continue
        if precedente:
            scarti["stessa legge già votata nell'altro ramo"] += 1
        tenute[c.chiave_atto] = c
    return sorted(tenute.values(), key=lambda c: (c.data, c.id_esterno)), dict(scarti)


def parametri_da_contenuti(parametri: dict) -> tuple[Parametri, float]:
    return Parametri.da_contenuti(parametri), float(Decimal(str(parametri["catalogo"]["minoranzaMinima"])))
