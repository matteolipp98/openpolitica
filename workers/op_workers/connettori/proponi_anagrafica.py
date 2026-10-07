"""Dal rapporto della sonda propone identificativi esterni e gruppi (ADR 0027).

Non scrive nei file di content/: stampa una proposta da rivedere e incollare in una pull request,
perché l'abbinamento persona-identificativo è una scelta che deve restare tracciata e rivista.

Uso: python -m op_workers.connettori.proponi_anagrafica sonde/rapporto.json
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

RE_DEPUTATO = re.compile(r"deputato\.rdf/d(\d+)_(\d+)$")
RE_SENATORE = re.compile(r"senatore/(\d+)$")
RE_GRUPPO = re.compile(r"gruppoParlamentare\.rdf/(gr\d+)$")
# "NOME (SIGLA) (GG.MM.AAAA" — la sigla può contenere parentesi, es. NM(N-C-U-I)M-CP
RE_ETICHETTA_GRUPPO = re.compile(
    r"^(?P<nome>.*?) \((?P<sigla>[^()]*(?:\([^()]*\)[^()]*)*)\) \((?P<dal>\d{2}\.\d{2}\.\d{4})"
)


def data_it(s: str) -> str:
    g, m, a = s.split(".")
    return date(int(a), int(m), int(g)).isoformat()


def gruppi_camera(r: dict[str, Any]) -> list[dict[str, str]]:
    out = []
    for riga in r["camera"].get("gruppi_legislatura", {}).get("righe", []):
        m_id = RE_GRUPPO.search(riga["g"])
        m_et = RE_ETICHETTA_GRUPPO.match(riga.get("nome", ""))
        if not (m_id and m_et):
            continue
        out.append(
            {
                "id_esterno": m_id.group(1),
                "nome": m_et.group("nome").strip(),
                "sigla": riga.get("sigla") or m_et.group("sigla"),
                "valido_dal": data_it(m_et.group("dal")),
            }
        )
    return out


def deputati(r: dict[str, Any]) -> list[dict[str, str]]:
    out = []
    for riga in r["camera"].get("leader", {}).get("righe", []):
        if m := RE_DEPUTATO.search(riga["d"]):
            out.append(
                {
                    "fonte": "camera",
                    "id": m.group(1),
                    "legislatura": m.group(2),
                    "nome": riga["nome"].title(),
                    "cognome": riga["cognome"].title(),
                }
            )
    return out


def senatori(r: dict[str, Any], con_mandato: set[str]) -> list[dict[str, str]]:
    out = []
    for riga in r["senato"].get("leader", {}).get("righe", []):
        if m := RE_SENATORE.search(riga["s"]):
            out.append(
                {
                    "fonte": "senato",
                    "id": m.group(1),
                    "nome": riga["nome"],
                    "cognome": riga["cognome"],
                    "mandato_xix": "sì" if riga["s"] in con_mandato else "non confermato",
                }
            )
    return out


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    r = json.loads(Path(argv[0]).read_text(encoding="utf8"))
    con_mandato = {x["s"] for x in r["senato"].get("mandati_leader", {}).get("righe", [])}
    print("# Gruppi Camera (legislatura in corso)")
    for g in gruppi_camera(r):
        print(f"- {g['id_esterno']}  {g['sigla']:<20} dal {g['valido_dal']}  {g['nome']}")
    print("\n# Deputati trovati tra i cognomi del perimetro")
    for d in deputati(r):
        print(f"- camera {d['id']:<8} {d['nome']} {d['cognome']}")
    print("\n# Senatori trovati tra i cognomi del perimetro (omonimi inclusi: scegliere a mano)")
    for s in senatori(r, con_mandato):
        print(f"- senato {s['id']:<8} {s['nome']} {s['cognome']}  mandato XIX: {s['mandato_xix']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
