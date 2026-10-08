"""Pacchetto di rilascio del sito (ADR 0005, 0025; piano §3.9).

Il sito non interroga il database: al build legge un pacchetto di file JSON, immutabile e con una versione.
Questo modulo lo costruisce dal database e da content/, nello stesso formato dei dati di esempio
(apps/web/lib/tipi.ts), così cambiando pacchetto non cambiano le pagine.

Contiene solo ciò che oggi esiste davvero: soggetti, domande e posizioni dai voti (se c'è il catalogo),
andamento nel tempo. Promesse, dati controllati e confronti parole–voti restano vuoti finché le fasi che
li producono non sono attive, e il manifest lo dice in `sezioni`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from datetime import UTC, date, datetime
from pathlib import Path

import yaml

from op_workers.andamento.da_voti import CALCOLO_VERSIONE as CALCOLO_ANDAMENTO
from op_workers.andamento.da_voti import da_database as andamento_da_database
from op_workers.connettori.base import pulisci_titolo
from op_workers.posizioni.da_voti import (
    CALCOLO_VERSIONE as CALCOLO_POSIZIONI,
)
from op_workers.posizioni.da_voti import (
    Evidenza,
    Parametri,
    orientamento_da_conteggi,
    orientamento_persona,
    posizione,
)

RADICE = Path(__file__).resolve().parents[3]
CONTENT = RADICE / "content"
MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre",
        "ottobre", "novembre", "dicembre"]  # fmt: skip


def leggi(rel: str) -> dict:
    return yaml.safe_load((CONTENT / rel).read_text(encoding="utf8"))


def _data(x) -> date | None:
    if x is None or isinstance(x, date):
        return x
    return date.fromisoformat(str(x))


def _attivo(periodo: dict, oggi: date) -> bool:
    dal, al = _data(periodo.get("valido_dal")), _data(periodo.get("valido_al"))
    return (dal is None or dal <= oggi) and (al is None or oggi <= al)


def quando(ramo: str, d: date) -> str:
    return f"{'Camera' if ramo == 'camera' else 'Senato'}, {d.day} {MESI[d.month - 1]} {d.year}"


# ---------- soggetti ----------


def soggetti(partiti: dict, perimetro: dict, alias: dict[str, dict], oggi: date) -> list[dict]:
    """Partiti e persone del perimetro, con il ruolo di oggi in parole semplici (ADR 0036)."""
    per_slug = {p["slug"]: p for p in partiti["partiti"]}
    chi_guida = guide(perimetro, alias)
    out = []
    for voce in perimetro["partiti"]:
        p = per_slug[voce["slug"]]
        ruolo = next((r["valore"] for r in p["ruolo"] if _attivo(r, oggi)), None)
        out.append({
            "id": p["slug"], "slug": p["slug"], "tipo": "partito", "nome": p["nome"],
            "ruolo": {"governo": "Al governo", "opposizione": "All'opposizione"}.get(ruolo, "Fuori dal Parlamento"),
            "guida": chi_guida.get(p["slug"], []),
        })  # fmt: skip
    for voce in perimetro["persone"]:
        a = alias[voce["slug"]]
        carica = next((c["carica"] for c in a["cariche"] if _attivo(c, oggi)), None)
        partito = per_slug[voce["partito"]]["nome"]
        out.append({
            "id": a["slug"], "slug": a["slug"], "tipo": "persona", "nome": f"{a['nome']} {a['cognome']}",
            "ruolo": f"{partito} · {carica}" if carica else partito, "partito": voce["partito"],
        })  # fmt: skip
    return out


# ---------- domande ----------


def domande(catalogo: dict | None) -> list[dict]:
    """Domande attive, con il ramo e il giorno del voto da cui vengono (la home mostra le più recenti)."""
    if not catalogo:
        return []
    out = []
    for e in catalogo["enunciati"]:
        if e["stato"] != "attivo":
            continue
        d = {"id": e["id"], "testo": e["testo"], "tema": e["tema"], "contesto": e["contesto"]}
        origine = e.get("origine") or {}
        if origine.get("data"):
            d["data"] = str(origine["data"])
        if (origine.get("votazione") or {}).get("ramo"):
            d["ramo"] = origine["votazione"]["ramo"]
        out.append(d)
    return out


# ---------- chi guida ogni partito (content/perimetro.yaml e content/alias/) ----------


def guide(perimetro: dict, alias: dict[str, dict]) -> dict[str, list[dict]]:
    """{partito: [{nome, slug}]}: le persone che seguiamo perché guidano il partito, nell'ordine del perimetro."""
    out: dict[str, list[dict]] = defaultdict(list)
    for voce in perimetro["persone"]:
        a = alias[voce["slug"]]
        out[voce["partito"]].append({"nome": f"{a['nome']} {a['cognome']}", "slug": a["slug"]})
    return dict(out)


# ---------- il Parlamento oggi: seggi per partito ----------

# Chi siede oggi in ogni ramo: l'ultima adesione a un gruppo ancora valida alla data. Il partito si attribuisce
# con la stessa regola dei voti (core.partito_alla_data): il gruppo se corrisponde a un solo partito, altrimenti
# l'appartenenza di partito della persona. Chi resta senza partito, o è in un partito che non seguiamo, va negli altri.
QUERY_SEGGI = """
with membri as (
  select distinct on (a.persona_id, g.ramo) a.persona_id, a.gruppo_id, g.ramo
  from core.appartenenza a join core.gruppo_parlamentare g on g.id = a.gruppo_id
  where a.tipo = 'gruppo' and g.legislatura = %(leg)s
    and a.valido_dal <= %(oggi)s and (a.valido_al is null or a.valido_al >= %(oggi)s)
  order by a.persona_id, g.ramo, a.valido_dal desc
)
select m.ramo, p.slug, count(*)
from membri m left join core.partito p on p.id = core.partito_alla_data(m.persona_id, m.gruppo_id, %(oggi)s)
group by 1, 2
"""


def parlamento(conn, partiti_ids: list[str], legislatura: int, oggi: date) -> dict:
    """{data, rami: {ramo: {totale, partiti: {slug: seggi}, altri}}}, alla data del pacchetto."""
    with conn.cursor() as cur:
        cur.execute(QUERY_SEGGI, {"leg": legislatura, "oggi": oggi})
        righe = cur.fetchall()
    rami: dict[str, dict] = {}
    for ramo, slug, n in righe:
        r = rami.setdefault(ramo, {"totale": 0, "partiti": dict.fromkeys(partiti_ids, 0), "altri": 0})
        r["totale"] += n
        if slug in r["partiti"]:
            r["partiti"][slug] += n
        else:
            r["altri"] += n
    return {"data": oggi.isoformat(), "rami": dict(sorted(rami.items()))}


# ---------- programmi: promesse per tema, promesse precise, programma comune ----------

ANNO = re.compile(r"\b(19|20)\d\d\b")
QUANDO = re.compile(r"\d|legislatura|\b(due|tre|quattro|cinque|sei|sette|otto|nove|dieci|cento)\b", re.IGNORECASE)


def precisa(orizzonte: str | None, misura: str, citazione: str) -> bool:
    """Una promessa "dice quanto e entro quando" (regola fissa, spiegata nella pagina del metodo):
    - entro quando: la scadenza letta nel programma c'è e contiene un numero ("entro il 2027", "in tre anni",
      "entro la legislatura"); "al più presto" o "da subito" non bastano;
    - quanto: nella misura o nella citazione c'è una cifra che non è un anno ("20.000 insegnanti", "10 miliardi").
    """
    if not orizzonte or not QUANDO.search(orizzonte):
        return False
    return any(re.search(r"\d", ANNO.sub(" ", t or "")) for t in (misura, citazione))


SEQUENZA = 6  # parole di fila confrontate tra due programmi
QUOTA_COMUNE = 0.5  # oltre questa quota di testo uguale, due programmi sono lo stesso programma


def _sequenze(testo: str) -> set[tuple[str, ...]]:
    parole = re.findall(r"\w+", testo.lower())
    return {tuple(parole[i : i + SEQUENZA]) for i in range(len(parole) - SEQUENZA + 1)}


def quota_testo_comune(a: str, b: str) -> float:
    """Quota del testo più corto che si ritrova uguale nell'altro, a gruppi di 6 parole di fila.
    Serve a riconoscere lo stesso programma depositato da più partiti in file diversi (il centrodestra nel 2022)."""
    sa, sb = _sequenze(a), _sequenze(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / min(len(sa), len(sb))


QUERY_PROGRAMMI = """
select distinct pa.slug, pr.elezione, d.id::text, d.sha256
from core.programma pr
join core.partito pa on pa.id = pr.partito_id
join core.documento dp on dp.id = pr.documento_id
join core.documento_attuale d on d.sha256 = dp.sha256
where pr.elezione = (select max(elezione) from core.programma)
"""
QUERY_TESTI = """
select documento_id::text, string_agg(testo, ' ' order by n)
from core.documento_paragrafo where documento_id = any(%s::uuid[]) group by 1
"""
QUERY_PROMESSE = """
select p.documento_id::text, p.orizzonte, p.misura, p.citazione, t.tema
from core.promessa_attuale p left join core.promessa_tema_attuale t on t.promessa_id = p.id
where p.documento_id = any(%s::uuid[])
"""


def programmi(conn, partiti_ids: list[str]) -> dict[str, dict]:
    """{partito: {elezione, promesse, precise: {n, d}, temi, comune?}} dall'ultimo programma depositato.

    I temi vengono da core.promessa_tema_attuale (issue #75); una promessa ancora senza tema non entra nelle barre."""
    with conn.cursor() as cur:
        cur.execute(QUERY_PROGRAMMI)
        prog = [r for r in cur.fetchall() if r[0] in partiti_ids]
        if not prog:
            return {}
        documenti = sorted({r[2] for r in prog})
        cur.execute(QUERY_PROMESSE, (documenti,))
        promesse = cur.fetchall()
        cur.execute(QUERY_TESTI, (documenti,))
        testi = dict(cur.fetchall())

    per_doc: dict[str, dict] = {}
    for doc in documenti:
        righe = [r for r in promesse if r[0] == doc]
        temi: dict[str, int] = defaultdict(int)
        for r in righe:
            if r[4]:
                temi[r[4]] += 1
        per_doc[doc] = {
            "promesse": len(righe),
            "precise": {"n": sum(precisa(r[1], r[2], r[3]) for r in righe), "d": len(righe)},
            "temi": dict(sorted(temi.items())),
        }

    out = {}
    for slug, elezione, doc, sha in prog:
        stesso = sorted(s for s, _, _, h in prog if h == sha and s != slug)
        simile = sorted(
            s for s, _, d2, h in prog
            if h != sha and s != slug and quota_testo_comune(testi.get(doc, ""), testi.get(d2, "")) > QUOTA_COMUNE
        )  # fmt: skip
        voce = {"elezione": elezione.isoformat(), **per_doc[doc]}
        if stesso or simile:
            voce["comune"] = {"stesso_documento": stesso, "testo_uguale": simile}
        out[slug] = voce
    return out


# ---------- posizioni dai voti ----------

QUERY_VOTAZIONI = """
select id::text, ramo, legislatura, id_esterno, data, coalesce(atto_titolo, descrizione, titolo, atto_ref, ''), url
from core.votazione where (ramo, legislatura, id_esterno) in (select * from unnest(%s::text[], %s::int[], %s::text[]))
"""
QUERY_PARTITI = """
select vg.votazione_id::text, p.slug, sum(vg.favorevoli), sum(vg.contrari), sum(vg.astenuti)
from core.votazione_gruppo vg
join core.votazione v on v.id = vg.votazione_id
join core.gruppo_partito gp on gp.gruppo_id = vg.gruppo_id
  and v.data >= gp.valido_dal and (gp.valido_al is null or v.data <= gp.valido_al)
join core.partito p on p.id = gp.partito_id
where vg.votazione_id = any(%s::uuid[])
  and (select count(*) from core.gruppo_partito g2 where g2.gruppo_id = vg.gruppo_id
       and v.data >= g2.valido_dal and (g2.valido_al is null or v.data <= g2.valido_al)) = 1
group by 1, 2
"""
QUERY_PERSONE = """
select vo.votazione_id::text, pe.slug, vo.espressione::text
from core.voto vo join core.persona pe on pe.id = vo.persona_id
where vo.votazione_id = any(%s::uuid[])
"""

FRASE_PARTITO = {1: "Ha votato a favore", -1: "Ha votato contro", 0: "Si è diviso"}
FRASE_PERSONA = {1: "Ha votato a favore", -1: "Ha votato contro", 0: "Si è astenuto"}


def _accorcia(t: str, n: int = 120) -> str:
    t = " ".join(t.split())
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


def posizioni(conn, catalogo: dict | None, sogg: list[dict], p: Parametri) -> dict:
    """{soggetto: {enunciato: Posizione}} con le evidenze di voto (ADR 0008, 0023)."""
    if not catalogo:
        return {}
    enunciati = [e for e in catalogo["enunciati"] if e["stato"] == "attivo"]
    chiavi = [(e["origine"]["votazione"]["ramo"], e["origine"]["votazione"]["legislatura"],
               e["origine"]["votazione"]["idEsterno"]) for e in enunciati]  # fmt: skip
    with conn.cursor() as cur:
        cur.execute(QUERY_VOTAZIONI, ([k[0] for k in chiavi], [k[1] for k in chiavi], [k[2] for k in chiavi]))
        vot = {(r[1], r[2], r[3]): r for r in cur.fetchall()}
        ids = [r[0] for r in vot.values()]
        cur.execute(QUERY_PARTITI, (ids,))
        partiti_voti = {(r[0], r[1]): r[2:] for r in cur.fetchall()}
        cur.execute(QUERY_PERSONE, (ids,))
        persone_voti = {(r[0], r[1]): r[2] for r in cur.fetchall()}

    out: dict[str, dict] = defaultdict(dict)
    for e, k in zip(enunciati, chiavi, strict=True):
        v = vot.get(k)
        for s in sogg:
            orient = None
            if v:
                if s["tipo"] == "partito":
                    conti = partiti_voti.get((v[0], s["id"]))
                    orient = orientamento_da_conteggi(*map(int, conti), p) if conti else None
                    frasi = FRASE_PARTITO
                else:
                    espr = persone_voti.get((v[0], s["id"]))
                    orient = orientamento_persona(espr) if espr else None
                    frasi = FRASE_PERSONA
            if orient is None:
                out[s["id"]][e["id"]] = {"valore": None, "stato": "non_documentata", "evidenze": []}
                continue
            pos = posizione([Evidenza(v[0], v[4].isoformat(), v[2], orient * e["origine"]["direzione"])], p)
            out[s["id"]][e["id"]] = {
                "valore": pos.valore,
                "stato": pos.stato,
                "evidenze": [
                    {
                        "testo": _accorcia(f"{frasi[orient]}: {pulisci_titolo(v[5])}" if v[5] else frasi[orient]),
                        "quando": quando(v[1], v[4]),
                        "url": v[6],
                    }
                ],  # fmt: skip
            }
    return dict(out)


# ---------- correzioni (ADR 0012) ----------


def _in_parole(valore) -> str:
    """prima/dopo sono jsonb: si mostra il campo `testo` se c'è, altrimenti il valore così com'è."""
    if isinstance(valore, dict) and "testo" in valore:
        return str(valore["testo"])
    return valore if isinstance(valore, str) else json.dumps(valore, ensure_ascii=False)


def correzioni(conn) -> list[dict]:
    """Tutte le correzioni pubblicate, dalla più recente. Non si cancella niente di nascosto."""
    with conn.cursor() as cur:
        cur.execute(
            """select pubblicata_il, oggetto_tipo, oggetto_id, prima, dopo, motivazione
               from core.correzione order by pubblicata_il desc"""
        )
        return [
            {"quando": q.date().isoformat(), "oggetto": f"{t}:{i}", "prima": _in_parole(p), "dopo": _in_parole(d),
             "motivo": m}
            for q, t, i, p, d, m in cur.fetchall()
        ]  # fmt: skip


# ---------- pacchetto ----------


def costruisci(conn, oggi: date | None = None, ora: datetime | None = None) -> dict[str, object]:
    ora = ora or datetime.now(UTC)
    oggi = oggi or ora.date()
    parametri = leggi("parametri.yaml")
    p = Parametri.da_contenuti(parametri)
    alias = {f.stem: yaml.safe_load(f.read_text(encoding="utf8")) for f in (CONTENT / "alias").glob("*.yaml")}
    sogg = soggetti(leggi("partiti.yaml"), leggi("perimetro.yaml"), alias, oggi)
    f_cat = CONTENT / "catalogo" / "v1" / "enunciati.yaml"
    catalogo = yaml.safe_load(f_cat.read_text(encoding="utf8")) if f_cat.exists() else None
    dom = domande(catalogo)
    pos = posizioni(conn, catalogo, sogg, p)

    andamento = andamento_da_database(conn, p.legislatura_riferimento, p.membri_minimi)
    partiti_ids = {s["id"] for s in sogg if s["tipo"] == "partito"}
    elenco_partiti = [s["id"] for s in sogg if s["tipo"] == "partito"]
    prog = programmi(conn, elenco_partiti)
    for s in sogg:
        if s["id"] in prog:
            s["programma"] = prog[s["id"]]
    andamento["serie"] = {k: v for k, v in andamento["serie"].items() if k in partiti_ids}
    andamento["governo"] = {k: v for k, v in andamento["governo"].items() if k in partiti_ids}

    with conn.cursor() as cur:
        cur.execute("select ramo, max(data) from core.votazione where legislatura = %s group by ramo",
                    (p.legislatura_riferimento,))  # fmt: skip
        ultime = {r[0]: r[1].isoformat() for r in cur.fetchall()}

    manifest = {
        "versione": ora.strftime("%Y.%m.%d-%H%M"),
        "esempio": False,
        "generato_il": oggi.isoformat(),
        "catalogo": {"versione": catalogo["versione"], "stato": catalogo["stato"]} if catalogo
        else {"versione": "nessuno", "stato": "provvisorio"},
        "sezioni": {"posizioni": bool(dom), "numeri": False, "coerenza": False, "promesse": False, "letture": False},
        "calcoli": {"posizioni": CALCOLO_POSIZIONI, "andamento": CALCOLO_ANDAMENTO, "affinita": "aff-1"},
        "fonti": {r: {"legislatura": p.legislatura_riferimento, "ultima_votazione": d} for r, d in ultime.items()},
    }  # fmt: skip
    return {
        "manifest.json": manifest,
        "domande.json": dom,
        "soggetti.json": sogg,
        "posizioni.json": pos,
        "accostamenti.json": {},
        "promesse.json": {},
        "andamento.json": andamento,
        "correzioni.json": correzioni(conn),
        "parlamento.json": parlamento(conn, elenco_partiti, p.legislatura_riferimento, oggi),
    }


def _json(x: object) -> bytes:
    return (json.dumps(x, ensure_ascii=False, indent=1, default=str) + "\n").encode("utf8")


def scrivi(file: dict[str, object], cartella: Path) -> dict:
    """Scrive i file e mette nel manifest l'impronta di ciascuno: chi scarica può verificarli."""
    cartella.mkdir(parents=True, exist_ok=True)
    manifest = dict(file["manifest.json"])  # type: ignore[arg-type]
    impronte = {}
    for nome, dati in file.items():
        if nome == "manifest.json":
            continue
        b = _json(dati)
        (cartella / nome).write_bytes(b)
        impronte[nome] = "sha256:" + hashlib.sha256(b).hexdigest()
    manifest["file"] = impronte
    (cartella / "manifest.json").write_bytes(_json(manifest))
    return manifest


def main(argv: list[str] | None = None) -> int:
    import psycopg

    ap = argparse.ArgumentParser(description="Costruisce il pacchetto di rilascio del sito")
    ap.add_argument("--uscita", type=Path, required=True)
    a = ap.parse_args(argv)
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        file = costruisci(conn)
    m = scrivi(file, a.uscita)
    n_sogg, n_dom = len(file["soggetti.json"]), len(file["domande.json"])  # type: ignore[arg-type]
    pos = "sì" if m["sezioni"]["posizioni"] else "no (manca il catalogo)"
    print(f"Pacchetto {m['versione']}: {n_sogg} soggetti, {n_dom} domande, posizioni {pos}")
    print(f"Ultime votazioni: {m['fonti']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
