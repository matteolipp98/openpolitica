"""Importa votazioni e voti di una legislatura da un connettore (piano §3.5).

Per ogni giorno con votazioni, in una sola transazione: si scaricano i voti, si controlla che
tornino con i totali, si inseriscono votazioni e voti. Idempotente: le righe già presenti non si toccano.
I parlamentari senza identità nota diventano persone automatiche (servono alle posizioni dei partiti),
mai fuse con persone esistenti (ADR 0027).

Uso: python -m op_workers.connettori.importa_voti camera|senato [--dal AAAA-MM-GG]  (con DATABASE_URL)
"""

from __future__ import annotations

import argparse
import os
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date

import psycopg

from op_workers.connettori.base import AdesioneGrezza, ConnettoreVoti, ParlamentareGrezzo, VotazioneGrezza, VotoGrezzo

INIZIO_LEGISLATURA = {19: date(2022, 10, 13)}


def inizio_legislatura(leg: int) -> date:
    if leg not in INIZIO_LEGISLATURA:
        raise ValueError(f"data di inizio della legislatura {leg} non configurata")
    return INIZIO_LEGISLATURA[leg]


@dataclass
class Rapporto:
    persone_nuove: int = 0
    adesioni_nuove: int = 0
    votazioni_nuove: int = 0
    voti_nuovi: int = 0
    non_attribuiti: int = 0
    incoerenti: list[str] = field(default_factory=list)


def coerente(v: VotazioneGrezza, voti: Iterable[VotoGrezzo]) -> bool:
    """I voti individuali devono tornare esattamente con i totali dichiarati (tolleranza zero)."""
    c = Counter(x.espressione for x in voti)
    return (c["favorevole"], c["contrario"], c["astenuto"]) == (v.favorevoli, v.contrari, v.astenuti)


def _gruppo(conn: psycopg.Connection, ramo: str, leg: int, id_esterno: str) -> str:
    conn.execute(
        """insert into core.gruppo_parlamentare (ramo, legislatura, id_esterno) values (%s, %s, %s)
           on conflict do nothing""",
        (ramo, leg, id_esterno),
    )
    return conn.execute(
        "select id from core.gruppo_parlamentare where ramo = %s and legislatura = %s and id_esterno = %s",
        (ramo, leg, id_esterno),
    ).fetchone()[0]


def mappa_persone(conn: psycopg.Connection, ramo: str) -> dict[str, str]:
    righe = conn.execute(
        "select id_esterno, persona_id::text from core.persona_id_esterno where fonte = %s", (ramo,)
    ).fetchall()
    return dict(righe)


def _assicura_persone(
    conn: psycopg.Connection, ramo: str, parlamentari: Iterable[ParlamentareGrezzo], leg: int, r: Rapporto
) -> dict[str, str]:
    noti = mappa_persone(conn, ramo)
    for p in parlamentari:
        if p.id_esterno in noti:
            continue
        slug = f"{ramo}-{p.id_esterno}"  # persona automatica fuori perimetro
        conn.execute(
            "insert into core.persona (slug, nome, cognome) values (%s, %s, %s) on conflict (slug) do nothing",
            (slug, p.nome, p.cognome),
        )
        conn.execute(
            """insert into core.persona_id_esterno (persona_id, fonte, id_esterno, valido_dal)
               select id, %s, %s, %s from core.persona where slug = %s on conflict do nothing""",
            (ramo, p.id_esterno, inizio_legislatura(leg), slug),
        )
        r.persone_nuove += 1
    return mappa_persone(conn, ramo)


def _importa_adesioni(
    conn: psycopg.Connection,
    ramo: str,
    leg: int,
    adesioni: Iterable[AdesioneGrezza],
    persone: dict[str, str],
    r: Rapporto,
) -> None:
    for a in adesioni:
        persona = persone.get(a.id_persona_esterno)
        if not persona:
            continue
        gruppo = _gruppo(conn, ramo, leg, a.id_gruppo_esterno)
        r.adesioni_nuove += conn.execute(
            """insert into core.appartenenza (persona_id, tipo, gruppo_id, valido_dal, valido_al, fonte_url)
               select %s, 'gruppo', %s, %s, %s, %s
               where not exists (select 1 from core.appartenenza
                                 where persona_id = %s and tipo = 'gruppo' and gruppo_id = %s and valido_dal = %s)""",
            (persona, gruppo, a.dal, a.al, f"{ramo}:adesione", persona, gruppo, a.dal),
        ).rowcount


def _gruppo_alla_data(conn: psycopg.Connection, persona: str, giorno: date) -> str | None:
    riga = conn.execute(
        """select gruppo_id from core.appartenenza
           where persona_id = %s and tipo = 'gruppo' and valido_dal <= %s and (valido_al is null or valido_al >= %s)
           order by valido_dal desc limit 1""",
        (persona, giorno, giorno),
    ).fetchone()
    return riga[0] if riga else None


def importa_giorno(
    conn: psycopg.Connection,
    c: ConnettoreVoti,
    leg: int,
    giorno: date,
    votazioni: list[VotazioneGrezza],
    persone: dict[str, str],
    r: Rapporto,
) -> None:
    per_votazione: dict[str, list[VotoGrezzo]] = defaultdict(list)
    for voto in c.voti_del_giorno(leg, giorno):
        per_votazione[voto.id_votazione_esterno].append(voto)

    for v in votazioni:
        voti = per_votazione.get(v.id_esterno, [])
        ok = coerente(v, voti)
        if not ok:
            r.incoerenti.append(f"{v.ramo}:{v.id_esterno}")
        riga = conn.execute(
            """insert into core.votazione (ramo, legislatura, id_esterno, data, tipo, titolo, descrizione, atto_ref,
                   atto_titolo, finale, fiducia, segreta, favorevoli, contrari, astenuti, approvata, url, coerente)
               values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               on conflict (ramo, legislatura, id_esterno) do nothing returning id""",
            (
                v.ramo,
                v.legislatura,
                v.id_esterno,
                v.data,
                v.tipo,
                v.titolo,
                v.descrizione,
                v.atto_ref,
                v.atto_titolo,
                v.finale,
                v.fiducia,
                v.segreta,
                v.favorevoli,
                v.contrari,
                v.astenuti,
                v.approvata,
                v.url,
                ok,
            ),
        ).fetchone()
        if not riga:  # già importata
            continue
        r.votazioni_nuove += 1
        for voto in voti:
            persona = persone.get(voto.id_persona_esterno)
            if not persona:
                conn.execute(
                    """insert into core.voto_non_attribuito (votazione_id, fonte, id_esterno, motivo)
                       values (%s, %s, %s, 'identificativo sconosciuto')""",
                    (riga[0], v.ramo, voto.id_persona_esterno),
                )
                r.non_attribuiti += 1
                continue
            gruppo = (
                _gruppo(conn, v.ramo, leg, voto.id_gruppo_esterno)
                if voto.id_gruppo_esterno
                else _gruppo_alla_data(conn, persona, v.data)
            )
            conn.execute(
                """insert into core.voto (votazione_id, persona_id, espressione, gruppo_id) values (%s, %s, %s, %s)
                   on conflict do nothing""",
                (riga[0], persona, voto.espressione, gruppo),
            )
            r.voti_nuovi += 1


def ultima_data(conn: psycopg.Connection, ramo: str, leg: int) -> date | None:
    return conn.execute(
        "select max(data) from core.votazione where ramo = %s and legislatura = %s", (ramo, leg)
    ).fetchone()[0]


def importa(conn: psycopg.Connection, c: ConnettoreVoti, leg: int, dal: date | None = None) -> Rapporto:
    """Import completo; ogni giorno è una transazione a sé, così un'interruzione non lascia giorni a metà."""
    r = Rapporto()
    with conn.transaction():
        persone = _assicura_persone(conn, c.ramo, c.parlamentari(leg), leg, r)
        _importa_adesioni(conn, c.ramo, leg, c.adesioni(leg), persone, r)
    inizio = dal or ultima_data(conn, c.ramo, leg) or inizio_legislatura(leg)
    per_giorno: dict[date, list[VotazioneGrezza]] = defaultdict(list)
    for v in c.votazioni(leg, inizio):
        per_giorno[v.data].append(v)
    for giorno in sorted(per_giorno):
        with conn.transaction():
            importa_giorno(conn, c, leg, giorno, per_giorno[giorno], persone, r)
    return r


def main(argv: list[str] | None = None) -> int:
    from op_workers.connettori.camera import ConnettoreCamera
    from op_workers.connettori.senato import ConnettoreSenato

    ap = argparse.ArgumentParser()
    ap.add_argument("ramo", choices=["camera", "senato"])
    ap.add_argument("--legislatura", type=int, default=19)
    ap.add_argument("--dal", type=date.fromisoformat)
    a = ap.parse_args(argv)
    c: ConnettoreVoti = ConnettoreCamera() if a.ramo == "camera" else ConnettoreSenato()
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
        r = importa(conn, c, a.legislatura, a.dal)
    print(r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
