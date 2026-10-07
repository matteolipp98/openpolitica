"""Genera il catalogo delle domande dalle votazioni (ADR 0030, con le regole dell'ADR 0038 per Gemini).

Passi:
1. candidate dai dati (candidati.py): votazioni finali, divisive, con partiti seguiti su fronti opposti;
2. generazione (una chiamata ogni LOTTO votazioni): tema, domanda, forma opposta, due riformulazioni,
   frasi di contesto; il modello può scartare le leggi "omnibus";
3. verifica (chiamata separata, alla cieca): per ogni frase, chi ha votato sì è d'accordo? e il tema;
4. test: tema confermato, sensibilità (domanda e riformulazioni d'accordo), polarità (opposto contrario);
5. selezione bilanciata: lo stesso numero di domande per tema (ADR 0022).

Ogni risposta del modello si salva in content/catalogo/<versione>/lavoro/ prima di proseguire: con
poche chiamate al giorno il job riprende da dove si era fermato. Il catalogo (enunciati.yaml) si scrive
solo quando tutte le candidate sono state elaborate.

Uso: python -m op_workers.catalogo.genera --versione v1 [--max-chiamate 20]  (DATABASE_URL, GEMINI_API_KEY)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import psycopg
import yaml

from op_workers.catalogo.candidati import Candidata, candidate, parametri_da_contenuti
from op_workers.catalogo.gemini import Gemini, QuotaEsaurita
from op_workers.catalogo.manuale import RispostaMancante, client

CONTENT = Path(__file__).resolve().parents[3] / "content"
PROMPT_VERSIONE = "v1"
LOTTO = 25
MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre",
        "ottobre", "novembre", "dicembre"]  # fmt: skip


def leggi(nome: str) -> dict:
    return yaml.safe_load((CONTENT / nome).read_text(encoding="utf8"))


def sha(testo: str) -> str:
    return hashlib.sha256(testo.encode()).hexdigest()


def temi_ruotati(temi: list[dict], seme: str) -> str:
    """Ordine dei temi diverso per ogni lotto: nessun tema è sempre il primo (ADR 0035)."""
    ordine = list(temi)
    random.Random(seme).shuffle(ordine)  # noqa: S311 - ordine riproducibile, non sicurezza
    return "\n".join(f"- {t['id']}: {t['nome']}. {t['descrizione']}" for t in ordine)


def schema_genera(temi_ids: list[str]) -> dict:
    return {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "id": {"type": "STRING"},
                "scarta": {"type": "BOOLEAN"},
                "motivo_scarto": {"type": "STRING"},
                "tema": {"type": "STRING", "enum": temi_ids},
                "enunciato": {"type": "STRING"},
                "opposto": {"type": "STRING"},
                "varianti": {"type": "ARRAY", "items": {"type": "STRING"}},
                "favorevoli": {"type": "STRING"},
                "contrari": {"type": "STRING"},
            },
            "required": ["id", "scarta"],
        },
    }


def schema_verifica(temi_ids: list[str]) -> dict:
    return {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "atto": {"type": "STRING"},
                "tema": {"type": "STRING", "enum": temi_ids},
                "frasi": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "id": {"type": "STRING"},
                            "risposta": {"type": "STRING", "enum": ["d_accordo", "contrario", "non_chiaro"]},
                        },
                        "required": ["id", "risposta"],
                    },
                },
            },
            "required": ["atto", "tema", "frasi"],
        },
    }


class Cache:
    def __init__(self, cartella: Path) -> None:
        self.cartella = cartella
        cartella.mkdir(parents=True, exist_ok=True)

    def leggi(self, chiave: str) -> dict | None:
        f = self.cartella / f"{chiave}.json"
        return json.loads(f.read_text(encoding="utf8")) if f.exists() else None

    def scrivi(self, chiave: str, dati: dict) -> None:
        (self.cartella / f"{chiave}.json").write_text(json.dumps(dati, ensure_ascii=False, indent=1) + "\n", "utf8")


def chiama(gemini: Gemini, cache: Cache, tipo: str, prompt: str, schema: dict, conn) -> dict:
    chiave = f"{tipo}-{sha(PROMPT_VERSIONE + prompt)[:16]}"
    if (salvato := cache.leggi(chiave)) is not None:
        return salvato
    r = gemini.json(prompt, schema)
    dati = {
        "modello": r.modello,
        "prompt_sha256": sha(prompt),
        "risposta": r.dati,
        "token_in": r.token_in,
        "token_out": r.token_out,
        "creato_il": datetime.now(UTC).isoformat(),
    }
    cache.scrivi(chiave, dati)
    if conn is not None:
        registra_run(conn, tipo, r, prompt)
    return dati


def registra_run(conn, tipo: str, r, prompt: str) -> None:
    conn.execute(
        """insert into core.modello (id, fornitore, famiglia) values (%s, %s, %s) on conflict do nothing""",
        (r.modello, r.fornitore, r.famiglia),
    )
    conn.execute(
        """insert into core.run_modello (stadio, modello_id, prompt_id, prompt_versione, input_sha256,
               prompt_renderizzato, output, token_in, token_out, latenza_ms)
           values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            f"catalogo.{tipo}",
            r.modello,
            f"catalogo/{tipo}",
            PROMPT_VERSIONE,
            sha(prompt),
            prompt,
            json.dumps(r.dati, ensure_ascii=False),
            r.token_in,
            r.token_out,
            r.latenza_ms,
        ),
    )
    conn.commit()


def prompt_genera(lotto: list[Candidata], temi: list[dict], seme: str) -> str:
    tpl = (CONTENT / "prompt/catalogo/genera.v1.md").read_text(encoding="utf8")
    atti = "\n".join(f"{c.id_esterno} | {c.atto_titolo}" for c in lotto)
    return tpl.replace("{temi}", temi_ruotati(temi, seme)).replace("{atti}", atti)


def frasi_da_verificare(g: dict) -> list[tuple[str, str]]:
    """(ruolo, testo): l'ordine viene mescolato prima di mandarle alla verifica."""
    return [("enunciato", g["enunciato"]), *[("variante", v) for v in g.get("varianti", [])[:2]],
            ("opposto", g["opposto"])]  # fmt: skip


def prompt_verifica(voci: list[tuple[Candidata, dict]], temi: list[dict], seme: str) -> tuple[str, dict]:
    """Restituisce il prompt e la mappa id frase → (id votazione, ruolo). La verifica non vede i ruoli."""
    tpl = (CONTENT / "prompt/catalogo/verifica.v1.md").read_text(encoding="utf8")
    rnd = random.Random(seme)  # noqa: S311 - ordine riproducibile, non sicurezza
    righe, mappa = [], {}
    for i, (c, g) in enumerate(voci, 1):
        frasi = frasi_da_verificare(g)
        rnd.shuffle(frasi)
        righe.append(f"Legge A{i}: {c.atto_titolo}")
        for j, (ruolo, testo) in enumerate(frasi, 1):
            fid = f"A{i}F{j}"
            mappa[fid] = (c.id_esterno, ruolo)
            righe.append(f"  {fid}: {testo}")
        mappa[f"A{i}"] = (c.id_esterno, "atto")
    return tpl.replace("{temi}", temi_ruotati(temi, seme + "v")).replace("{atti}", "\n".join(righe)), mappa


def data_italiana(d) -> str:
    return f"{d.day} {MESI[d.month - 1]} {d.year}"


def costruisci_enunciato(c: Candidata, g: dict, v: dict, modello: str) -> dict:
    risposte = v["risposte"]
    sens = all(r == "d_accordo" for ruolo, r in risposte if ruolo in ("enunciato", "variante"))
    pol = all(r == "contrario" for ruolo, r in risposte if ruolo == "opposto")
    esito = "approvata" if c.approvata else "respinta" if c.approvata is False else "votata"
    ramo = "alla Camera" if c.ramo == "camera" else "al Senato"
    return {
        "id": "e-" + f"{c.ramo}-{c.id_esterno}".lower().replace("_", "-"),
        "versione": 1,
        "testo": g["enunciato"].strip(),
        "tema": g["tema"],
        "livelloGoverno": "nazionale",
        "stato": "attivo",
        "contesto": {
            "fatto": f"Se n'è votato {ramo} il {data_italiana(c.data)}: la legge è stata {esito}.",
            "favorevoli": g["favorevoli"].strip(),
            "contrari": g["contrari"].strip(),
        },
        "origine": {
            "votazione": {"ramo": c.ramo, "legislatura": 19, "idEsterno": c.id_esterno},
            "atto": c.atto_ref,
            "data": c.data.isoformat(),
            "direzione": 1,
            "generazione": {"modello": modello, "promptVersione": PROMPT_VERSIONE,
                            "inputSha256": sha(c.atto_titolo)},
        },
        "test": {
            "divisivita": {"superato": True, "dettagli": {"minoranza": round(c.minoranza, 3)}},
            "discriminazione": {"superato": True, "dettagli": {"orientamenti": c.orientamenti}},
            "tema": {"superato": v["tema"] == g["tema"], "dettagli": {"verifica": v["tema"]}},
            "sensibilita": {"superato": sens, "dettagli": {}},
            "polarita": {"superato": pol, "dettagli": {}},
        },
    }  # fmt: skip


def chiave_votazione(e: dict) -> tuple[str, str]:
    v = e["origine"]["votazione"]
    return v["ramo"], v["idEsterno"]


def esclusioni(cartella: Path) -> set[tuple[str, str]]:
    """Votazioni tolte a mano con motivo pubblico (esclusioni.yaml): dopo la generazione, così la cache resta valida."""
    f = cartella / "esclusioni.yaml"
    if not f.exists():
        return set()
    voci = yaml.safe_load(f.read_text(encoding="utf8")).get("esclusioni") or []
    for x in voci:
        if not str(x.get("motivo", "")).strip():
            raise ValueError(f"esclusione senza motivo: {x}")
    return {(x["votazione"]["ramo"], str(x["votazione"]["idEsterno"])) for x in voci}


def seleziona(enunciati: list[dict], temi_ids: list[str], per_tema: int) -> tuple[list[dict], int]:
    """Stesso numero per tema (ADR 0022): k = il minimo tra per_tema e il tema più povero."""
    per = defaultdict(list)
    for e in enunciati:
        per[e["tema"]].append(e)
    for lista in per.values():  # preferenza: più divisive; a parità, più recenti
        lista.sort(key=lambda e: e["origine"]["data"], reverse=True)
        lista.sort(key=lambda e: -e["test"]["divisivita"]["dettagli"]["minoranza"])
    visti: set[str] = set()  # la stessa legge votata due volte può dare la stessa domanda: una sola (ADR 0030)
    for t in list(per):
        unici = []
        for e in per[t]:
            chiave = " ".join(e.get("testo", "").casefold().split())
            if not chiave or chiave not in visti:
                visti.add(chiave)
                unici.append(e)
        per[t] = unici
    k = min([per_tema] + [len(per[t]) for t in temi_ids])
    return [e for t in temi_ids for e in per[t][:k]], k


def import_incompleto(conn, giorni: int = 30) -> str | None:
    """Le chiamate si fanno solo con i voti di entrambi i rami importati fino a date recenti:
    con un import a metà i lotti cambierebbero e la cache non servirebbe più."""
    ultime = dict(conn.execute("select ramo, max(data) from core.votazione where legislatura = 19 group by ramo"))
    for ramo in ("camera", "senato"):
        if ramo not in ultime:
            return f"nessuna votazione importata per {ramo}"
        if (datetime.now(UTC).date() - ultime[ramo]).days > giorni:
            return f"l'import di {ramo} è fermo al {ultime[ramo]}"
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--versione", default="v1")
    ap.add_argument("--max-chiamate", type=int, default=20)
    a = ap.parse_args(argv)

    temi = leggi("temi.yaml")["temi"]
    temi_ids = [t["id"] for t in temi]
    parametri = leggi("parametri.yaml")
    perimetro = {p["slug"] for p in leggi("perimetro.yaml")["partiti"]}
    p, minoranza = parametri_da_contenuti(parametri)
    cartella = CONTENT / "catalogo" / a.versione
    cache = Cache(cartella / "lavoro")
    gemini = client(a.max_chiamate)

    conn = psycopg.connect(os.environ["DATABASE_URL"])
    if motivo := import_incompleto(conn):
        conn.close()
        print(f"Catalogo rimandato: {motivo}. Nessuna chiamata a Gemini.")
        return 0
    cands, scarti = candidate(conn, 19, perimetro, p, minoranza)
    print(f"Candidate: {len(cands)}; scartate dai dati: {scarti}")
    if not cands:
        conn.close()
        print("Nessuna votazione candidata: i voti non sono ancora stati importati. Nessuna chiamata a Gemini.")
        return 0

    generate: dict[str, dict] = {}
    verifiche: dict[str, dict] = {}
    modello = gemini.modello
    lotti = [cands[i : i + LOTTO] for i in range(0, len(cands), LOTTO)]
    completo = True
    elaborate = 0
    try:
        for n, lotto in enumerate(lotti, 1):
            seme = f"{a.versione}-{n}"
            try:
                g = chiama(gemini, cache, "genera", prompt_genera(lotto, temi, seme), schema_genera(temi_ids), conn)
            except RispostaMancante:  # client a mano (#71): il lotto aspetta la risposta, si va avanti
                completo = False
                continue
            modello = g["modello"]
            elaborate += len(lotto)
            per_id = {x["id"]: x for x in g["risposta"]}
            voci = [(c, per_id[c.id_esterno]) for c in lotto
                    if c.id_esterno in per_id and not per_id[c.id_esterno].get("scarta")
                    and all(per_id[c.id_esterno].get(k) for k in ("tema", "enunciato", "opposto"))]  # fmt: skip
            for c, x in voci:
                generate[c.id_esterno] = x
            if not voci:
                continue
            pv, mappa = prompt_verifica(voci, temi, seme)
            try:
                v = chiama(gemini, cache, "verifica", pv, schema_verifica(temi_ids), conn)
            except RispostaMancante:
                completo = False
                continue
            for atto in v["risposta"]:
                ide, _ = mappa.get(atto["atto"], (None, None))
                if ide is None:
                    continue
                risposte = [(mappa[f["id"]][1], f["risposta"]) for f in atto["frasi"] if f["id"] in mappa]
                verifiche[ide] = {"tema": atto["tema"], "risposte": risposte}
            print(f"Lotto {n}/{len(lotti)} fatto ({gemini.chiamate} chiamate in questa esecuzione)")
    except QuotaEsaurita as e:
        completo = False
        print(f"Fermato: {e}. Le risposte già ottenute sono in cache: si riprende al prossimo giro.")
    finally:
        conn.close()
    if getattr(gemini, "mancanti", None):
        print(f"Prompt in attesa di una risposta scritta a mano: {len(gemini.mancanti)} (#71)")

    per_cand = {c.id_esterno: c for c in cands}
    costruiti = [costruisci_enunciato(per_cand[i], generate[i], verifiche[i], modello)
                 for i in generate if i in verifiche]  # fmt: skip
    esclusi = esclusioni(cartella)
    costruiti_tutti, costruiti = costruiti, [e for e in costruiti if chiave_votazione(e) not in esclusi]
    superati = [e for e in costruiti if all(t["superato"] for t in e["test"].values())]
    rapporto = {
        "versione": a.versione,
        "aggiornato_il": datetime.now(UTC).isoformat(timespec="seconds"),
        "modello": modello,
        "completo": completo,
        "candidate": len(cands),
        "scartate_dai_dati": scarti,
        "scartate_dal_modello": elaborate - len(generate),
        "generate": len(generate),
        "verificate": len(costruiti_tutti),
        "escluse_a_mano": len(costruiti_tutti) - len(costruiti),
        "test_superati": len(superati),
        "test_falliti": {
            k: sum(1 for e in costruiti if not e["test"][k]["superato"]) for k in ("tema", "sensibilita", "polarita")
        },  # fmt: skip
        "per_tema": {t: sum(1 for e in superati if e["tema"] == t) for t in temi_ids},
    }
    (cartella / "rapporto-test.json").write_text(json.dumps(rapporto, ensure_ascii=False, indent=2) + "\n", "utf8")
    print(json.dumps(rapporto, ensure_ascii=False, indent=2))

    if not completo:
        return 0
    scelti, k = seleziona(superati, temi_ids, parametri["catalogo"]["enunciatiPerTema"])
    if k < 3:
        print(f"Catalogo non scritto: il tema più povero ha solo {k} domande valide (servono almeno 3).")
        return 1
    catalogo = {
        "versione": a.versione,
        "stato": "provvisorio",
        "nota": "Domande scritte e controllate da un solo sistema di intelligenza artificiale (ADR 0038).",
        "generato_il": datetime.now(UTC).isoformat(timespec="seconds"),
        "enunciatiPerTema": k,
        "enunciati": scelti,
    }
    (cartella / "enunciati.yaml").write_text(
        yaml.safe_dump(catalogo, allow_unicode=True, sort_keys=False, width=110), encoding="utf8"
    )
    print(f"Catalogo scritto: {len(scelti)} domande, {k} per tema.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
