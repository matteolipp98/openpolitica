"""Importa votazioni e voti di una legislatura da un connettore (piano §3.5).

Cosa si salva (vincolo di spazio: i voti individuali sono ~10 milioni di righe):
- ogni votazione, con il controllo che i voti individuali tornino con i totali;
- per ogni votazione e gruppo parlamentare, i conteggi (core.votazione_gruppo): bastano per le
  posizioni dei partiti;
- il voto individuale (core.voto) solo per le persone del perimetro e per i membri dei gruppi formati
  da più partiti, dove il gruppo non basta a dire a quale partito attribuire il voto (ADR 0027).

Per ogni giorno con votazioni, una sola transazione. Idempotente: le votazioni già presenti si saltano.
Le righe si inseriscono a blocchi (il database può essere lontano dal worker).

Uso: python -m op_workers.connettori.importa_voti camera|senato [--dal AAAA-MM-GG]  (con DATABASE_URL)
"""

from __future__ import annotations

import argparse
import logging
import os
import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date

import psycopg

from op_workers.comuni.sparql import ErroreSparql
from op_workers.connettori.base import ConnettoreVoti, ParlamentareGrezzo, VotazioneGrezza, VotoGrezzo

log = logging.getLogger(__name__)

INIZIO_LEGISLATURA = {19: date(2022, 10, 13)}
BLOCCO_VOTAZIONI = 20  # votazioni salvate insieme quando la fonte va interrogata una votazione per volta
NESSUN_GRUPPO = None


def inizio_legislatura(leg: int) -> date:
    if leg not in INIZIO_LEGISLATURA:
        raise ValueError(f"data di inizio della legislatura {leg} non configurata")
    return INIZIO_LEGISLATURA[leg]


@dataclass
class Rapporto:
    persone_nuove: int = 0
    adesioni_nuove: int = 0
    votazioni_nuove: int = 0
    voti_individuali: int = 0
    conteggi_gruppo: int = 0
    non_attribuiti: int = 0
    atti_corretti: int = 0
    incoerenti: list[str] = field(default_factory=list)
    interrotto: str | None = None  # la fonte ci ha bloccato: si riprende al prossimo giro


def conteggi(espressioni: Iterable[str]) -> tuple[int, int, int, int]:
    c = Counter(espressioni)
    fav, con, ast = c.pop("favorevole", 0), c.pop("contrario", 0), c.pop("astenuto", 0)
    return fav, con, ast, sum(c.values())


class Contesto:
    """Anagrafica di un ramo tenuta in memoria per tutto l'import: niente query per singolo voto."""

    def __init__(self, conn: psycopg.Connection, ramo: str, leg: int) -> None:
        self.conn, self.ramo, self.leg = conn, ramo, leg
        self.persone: dict[str, str] = {}
        self.gruppi: dict[str, str] = {}
        self.adesioni: dict[str, list[tuple[date, date | None, str]]] = defaultdict(list)
        self.partiti_gruppo: dict[str, list[tuple[date, date | None]]] = defaultdict(list)
        self.perimetro: set[str] = set()
        self.perimetro_esterni: set[str] = set()
        self.gruppi_misti_esterni: set[str] = set()
        self.ricarica()

    def ricarica(self) -> None:
        c, ramo, leg = self.conn, self.ramo, self.leg
        self.persone = dict(
            c.execute(
                "select id_esterno, persona_id::text from core.persona_id_esterno where fonte = %s", (ramo,)
            ).fetchall()
        )
        self.gruppi = dict(
            c.execute(
                "select id_esterno, id::text from core.gruppo_parlamentare where ramo = %s and legislatura = %s",
                (ramo, leg),
            ).fetchall()
        )
        self.adesioni.clear()
        for persona, dal, al, gruppo in c.execute(
            """select a.persona_id::text, a.valido_dal, a.valido_al, a.gruppo_id::text
               from core.appartenenza a join core.gruppo_parlamentare g on g.id = a.gruppo_id
               where a.tipo = 'gruppo' and g.ramo = %s and g.legislatura = %s""",
            (ramo, leg),
        ):
            self.adesioni[persona].append((dal, al, gruppo))
        self.partiti_gruppo.clear()
        for gruppo, dal, al in c.execute("select gruppo_id::text, valido_dal, valido_al from core.gruppo_partito"):
            self.partiti_gruppo[gruppo].append((dal, al))
        # Persone del perimetro: quelle con identità da content/ (le automatiche hanno slug "<ramo>-<id>")
        self.perimetro = {
            r[0]
            for r in c.execute("select id::text from core.persona where slug not similar to '(camera|senato)-[0-9]+'")
        }
        self.perimetro_esterni = {e for e, p in self.persone.items() if p in self.perimetro}
        # Gruppi che in qualche periodo sono di più partiti: i loro voti servono uno per uno
        self.gruppi_misti_esterni = {e for e, g in self.gruppi.items() if len(self.partiti_gruppo.get(g, [])) > 1}

    def gruppo(self, id_esterno: str) -> str:
        if id_esterno not in self.gruppi:
            self.gruppi[id_esterno] = self.conn.execute(
                """insert into core.gruppo_parlamentare (ramo, legislatura, id_esterno) values (%s, %s, %s)
                   on conflict (ramo, legislatura, id_esterno) do update set id_esterno = excluded.id_esterno
                   returning id::text""",
                (self.ramo, self.leg, id_esterno),
            ).fetchone()[0]
        return self.gruppi[id_esterno]

    def gruppo_alla_data(self, persona: str, giorno: date) -> str | None:
        validi = [
            (dal, g) for dal, al, g in self.adesioni.get(persona, []) if dal <= giorno and (al is None or giorno <= al)
        ]
        return max(validi)[1] if validi else None  # a parità vale l'adesione iniziata per ultima

    def gruppo_di_piu_partiti(self, gruppo: str | None, giorno: date) -> bool:
        if gruppo is None:
            return False
        return (
            sum(1 for dal, al in self.partiti_gruppo.get(gruppo, []) if dal <= giorno and (al is None or giorno <= al))
            > 1
        )

    def salva_individuale(self, persona: str, gruppo: str | None, giorno: date) -> bool:
        return persona in self.perimetro or self.gruppo_di_piu_partiti(gruppo, giorno)


def assicura_persone(ctx: Contesto, parlamentari: Iterable[ParlamentareGrezzo], r: Rapporto) -> None:
    nuovi = [p for p in parlamentari if p.id_esterno not in ctx.persone]
    with ctx.conn.cursor() as cur:
        cur.executemany(
            "insert into core.persona (slug, nome, cognome) values (%s, %s, %s) on conflict (slug) do nothing",
            [(f"{ctx.ramo}-{p.id_esterno}", p.nome, p.cognome) for p in nuovi],
        )
        cur.executemany(
            """insert into core.persona_id_esterno (persona_id, fonte, id_esterno, valido_dal)
               select id, %s, %s, %s from core.persona where slug = %s on conflict do nothing""",
            [(ctx.ramo, p.id_esterno, inizio_legislatura(ctx.leg), f"{ctx.ramo}-{p.id_esterno}") for p in nuovi],
        )
    r.persone_nuove += len(nuovi)


def importa_adesioni(ctx: Contesto, adesioni: Iterable, r: Rapporto) -> None:
    esistenti = {(p, dal, g) for p, lista in ctx.adesioni.items() for dal, _, g in lista}
    righe = []
    for a in adesioni:
        persona = ctx.persone.get(a.id_persona_esterno)
        if not persona:
            continue
        gruppo = ctx.gruppo(a.id_gruppo_esterno)
        if (persona, a.dal, gruppo) not in esistenti:
            esistenti.add((persona, a.dal, gruppo))
            righe.append((persona, gruppo, a.dal, a.al, f"{ctx.ramo}:adesione"))
    with ctx.conn.cursor() as cur:
        cur.executemany(
            """insert into core.appartenenza (persona_id, tipo, gruppo_id, valido_dal, valido_al, fonte_url)
               values (%s, 'gruppo', %s, %s, %s, %s)""",
            righe,
        )
    r.adesioni_nuove += len(righe)


def _voti_del_giorno(
    ctx: Contesto, c: ConnettoreVoti, giorno: date, ids: list[str] | None = None
) -> tuple[dict[str, Counter], dict[str, list[VotoGrezzo]]]:
    """Per ogni votazione: conteggi per (gruppo esterno, espressione) dei voti con gruppo noto, e i voti
    da trattare uno per uno (senza gruppo, persone del perimetro, gruppi di più partiti).

    Se la fonte sa contare (Camera) si scaricano i conteggi e solo i voti che servono: ~20 volte più veloce.
    Altrimenti (Senato) si scaricano tutti i voti e si contano qui.
    """
    conti: dict[str, Counter] = defaultdict(Counter)
    singoli: dict[str, list[VotoGrezzo]] = defaultdict(list)
    if hasattr(c, "conteggi_del_giorno"):
        for k in c.conteggi_del_giorno(ctx.leg, giorno):
            if k.id_gruppo_esterno is not None:  # i voti senza gruppo arrivano uno per uno qui sotto
                conti[k.id_votazione_esterno][(k.id_gruppo_esterno, k.espressione)] += k.n
        for voto in c.voti_scelti_del_giorno(ctx.leg, giorno, ctx.perimetro_esterni, ctx.gruppi_misti_esterni):
            singoli[voto.id_votazione_esterno].append(voto)
        return conti, singoli
    voti = (
        c.voti_delle_votazioni(ctx.leg, giorno, ids)  # type: ignore[attr-defined]
        if ids is not None and hasattr(c, "voti_delle_votazioni")
        else c.voti_del_giorno(ctx.leg, giorno)
    )
    for voto in voti:
        if voto.id_gruppo_esterno is not None:
            conti[voto.id_votazione_esterno][(voto.id_gruppo_esterno, voto.espressione)] += 1
        singoli[voto.id_votazione_esterno].append(voto)
    return conti, singoli


def importa_giorno(
    ctx: Contesto, c: ConnettoreVoti, giorno: date, votazioni: list[VotazioneGrezza], r: Rapporto
) -> None:
    conti, singoli = _voti_del_giorno(ctx, c, giorno, [v.id_esterno for v in votazioni])

    righe_gruppo, righe_voto, righe_ignote = [], [], []
    for v in votazioni:
        per_gruppo: dict[str | None, Counter] = defaultdict(Counter)
        for (gruppo_esterno, espr), n in conti.get(v.id_esterno, Counter()).items():
            per_gruppo[ctx.gruppo(gruppo_esterno)][espr] += n
        individuali = []
        for voto in singoli.get(v.id_esterno, []):
            persona = ctx.persone.get(voto.id_persona_esterno)
            if voto.id_gruppo_esterno:
                gruppo = ctx.gruppo(voto.id_gruppo_esterno)
            else:  # senza gruppo nel dato: quello a cui aderiva quel giorno, e si conta qui
                gruppo = ctx.gruppo_alla_data(persona, v.data) if persona else NESSUN_GRUPPO
                per_gruppo[gruppo][voto.espressione] += 1
            individuali.append((voto, persona, gruppo))

        totali: Counter = Counter()
        for cont in per_gruppo.values():
            totali.update(cont)
        ok = (totali["favorevole"], totali["contrario"], totali["astenuto"]) == (v.favorevoli, v.contrari, v.astenuti)
        if not ok:
            r.incoerenti.append(f"{v.ramo}:{v.id_esterno}")
        riga = ctx.conn.execute(
            """insert into core.votazione (ramo, legislatura, id_esterno, data, tipo, titolo, descrizione, atto_ref,
                   atto_titolo, finale, fiducia, segreta, favorevoli, contrari, astenuti, approvata, url, coerente)
               values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               on conflict (ramo, legislatura, id_esterno) do nothing returning id::text""",
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
        vid = riga[0]
        r.votazioni_nuove += 1

        for voto, persona, gruppo in individuali:
            if not persona:
                righe_ignote.append((vid, v.ramo, voto.id_persona_esterno))
            elif ctx.salva_individuale(persona, gruppo, v.data):
                righe_voto.append((vid, persona, voto.espressione, gruppo))
        for gruppo, cont in per_gruppo.items():
            righe_gruppo.append((vid, gruppo, *conteggi(cont.elements())))

    with ctx.conn.cursor() as cur:
        cur.executemany(
            """insert into core.votazione_gruppo (votazione_id, gruppo_id, favorevoli, contrari, astenuti, altri)
               values (%s, %s, %s, %s, %s, %s)""",
            righe_gruppo,
        )
        cur.executemany(
            """insert into core.voto (votazione_id, persona_id, espressione, gruppo_id) values (%s, %s, %s, %s)
               on conflict do nothing""",
            righe_voto,
        )
        cur.executemany(
            """insert into core.voto_non_attribuito (votazione_id, fonte, id_esterno, motivo)
               values (%s, %s, %s, 'identificativo sconosciuto')""",
            righe_ignote,
        )
    r.conteggi_gruppo += len(righe_gruppo)
    r.voti_individuali += len(righe_voto)
    r.non_attribuiti += len(righe_ignote)


def ultima_data(conn: psycopg.Connection, ramo: str, leg: int) -> date | None:
    return conn.execute(
        "select max(data) from core.votazione where ramo = %s and legislatura = %s", (ramo, leg)
    ).fetchone()[0]


def importa(conn: psycopg.Connection, c: ConnettoreVoti, leg: int, dal: date | None = None) -> Rapporto:
    """Import completo e ripetibile: le votazioni già importate si saltano. Per la Camera ogni giorno è una
    transazione; per il Senato ogni blocco di BLOCCO_VOTAZIONI votazioni."""
    r = Rapporto()
    with conn.transaction():
        ctx = Contesto(conn, c.ramo, leg)
        assicura_persone(ctx, c.parlamentari(leg), r)
        ctx.ricarica()
        importa_adesioni(ctx, c.adesioni(leg), r)
        ctx.ricarica()
    inizio = dal or ultima_data(conn, c.ramo, leg) or inizio_legislatura(leg)
    per_giorno: dict[date, list[VotazioneGrezza]] = defaultdict(list)
    for v in c.votazioni(leg, inizio):
        per_giorno[v.data].append(v)
    giorni = sorted(per_giorno)
    for i, giorno in enumerate(giorni, 1):
        esistenti = {
            x[0]
            for x in conn.execute(
                "select id_esterno from core.votazione where ramo = %s and legislatura = %s and data = %s",
                (c.ramo, leg, giorno),
            )
        }
        nuove = [v for v in per_giorno[giorno] if v.id_esterno not in esistenti]
        # Dove i voti si chiedono una votazione per volta (Senato) si salva a blocchi: se la fonte ci blocca
        # a metà di un giorno con centinaia di votazioni, i blocchi fatti restano e il giro dopo riparte da lì.
        passo = BLOCCO_VOTAZIONI if hasattr(c, "voti_delle_votazioni") else max(1, len(nuove))
        try:
            for k in range(0, len(nuove), passo):
                with conn.transaction():
                    importa_giorno(ctx, c, giorno, nuove[k : k + passo], r)
        except ErroreSparql as e:
            if not re.search(r"HTTP (403|429|5\d\d)", str(e)):
                raise
            # Blocco per troppe richieste o server sovraccarico (anche dopo i tentativi): ciò che è già
            # stato salvato resta, il prossimo giro riparte da qui
            r.interrotto = f"{c.ramo}: bloccato dalla fonte al {giorno} ({e})"
            log.warning(r.interrotto)
            break
        if i % 20 == 0 or i == len(giorni):
            log.info("%s: %d/%d giorni, %d votazioni nuove", c.ramo, i, len(giorni), r.votazioni_nuove)
    if hasattr(c, "atti_votazioni_finali") and not r.interrotto:
        correggi_atti(conn, c, leg, r)
    return r


def correggi_atti(conn: psycopg.Connection, c, leg: int, r: Rapporto) -> None:
    """Riallinea atto e titolo delle votazioni finali già salvate con la scelta attuale del connettore (#74).

    L'import salta le votazioni già presenti: senza questo passo un titolo sbagliato resterebbe per sempre.
    """
    try:
        atti = c.atti_votazioni_finali(leg)
    except ErroreSparql as e:
        if not re.search(r"HTTP (403|429|5\d\d)", str(e)):
            raise
        log.warning("%s: atti delle votazioni finali non letti, si riprova al prossimo giro (%s)", c.ramo, e)
        return
    with conn.transaction(), conn.cursor() as cur:
        cur.executemany(
            """update core.votazione set atto_ref = %s, atto_titolo = %s
               where ramo = %s and legislatura = %s and id_esterno = %s
                 and (atto_ref, atto_titolo) is distinct from (%s, %s)""",
            [(ref, tit, c.ramo, leg, ide, ref, tit) for ide, (ref, tit) in sorted(atti.items())],
        )
        r.atti_corretti += max(cur.rowcount, 0)


def main(argv: list[str] | None = None) -> int:
    from op_workers.connettori.camera import ConnettoreCamera
    from op_workers.connettori.senato import ConnettoreSenato

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("ramo", choices=["camera", "senato"])
    ap.add_argument("--legislatura", type=int, default=19)
    ap.add_argument("--dal", type=date.fromisoformat)
    a = ap.parse_args(argv)
    c: ConnettoreVoti = ConnettoreCamera() if a.ramo == "camera" else ConnettoreSenato()
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
        r = importa(conn, c, a.legislatura, a.dal)
    print(r)
    return 1 if r.incoerenti and len(r.incoerenti) > max(10, r.votazioni_nuove // 100) else 0


if __name__ == "__main__":
    raise SystemExit(main())
