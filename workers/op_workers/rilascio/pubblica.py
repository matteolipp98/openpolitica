"""Pubblica un pacchetto di rilascio su Supabase Storage (piano §3.9).

Ogni versione resta per sempre in rilasci/<versione>/ (dataset pubblico e riproducibile, ADR 0005, 0025);
rilasci/corrente.json dice quale versione usa il sito. Il passaggio a una versione nuova è registrato in
core.rilascio. La chiave è SUPABASE_SECRET_KEY e non lascia mai GitHub Actions.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import httpx

BUCKET = "rilasci"


def _client(url: str, chiave: str, transport: httpx.BaseTransport | None = None) -> httpx.Client:
    return httpx.Client(
        base_url=url.rstrip("/") + "/storage/v1",
        headers={"apikey": chiave, "Authorization": f"Bearer {chiave}"},
        timeout=60,
        transport=transport,
    )


def assicura_bucket(c: httpx.Client) -> None:
    r = c.post("/bucket", json={"id": BUCKET, "name": BUCKET, "public": True})
    if r.status_code in (200, 201) or "already exists" in r.text.lower() or "duplicate" in r.text.lower():
        return
    raise RuntimeError(f"bucket {BUCKET}: HTTP {r.status_code} {r.text[:200]}")


def carica(c: httpx.Client, percorso: str, corpo: bytes, sovrascrivi: bool = False) -> None:
    r = c.post(
        f"/object/{BUCKET}/{percorso}",
        content=corpo,
        headers={
            "Content-Type": "application/json",
            "x-upsert": "true" if sovrascrivi else "false",
            "cache-control": "max-age=60" if sovrascrivi else "max-age=31536000, immutable",
        },
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"caricamento {percorso}: HTTP {r.status_code} {r.text[:200]}")


def pubblica(cartella: Path, c: httpx.Client) -> dict:
    manifest = json.loads((cartella / "manifest.json").read_text(encoding="utf8"))
    v = manifest["versione"]
    assicura_bucket(c)
    for f in sorted(cartella.glob("*.json")):
        carica(c, f"{v}/{f.name}", f.read_bytes())
    carica(c, "corrente.json", json.dumps({"versione": v}).encode(), sovrascrivi=True)
    return manifest


def registra(conn, manifest: dict) -> None:
    conn.execute(
        """insert into core.rilascio (versione, catalogo_versione, calcolo_versione, manifest, storage_path)
           values (%s, %s, %s, %s, %s) on conflict (versione) do nothing""",
        (
            manifest["versione"],
            manifest["catalogo"]["versione"],
            f"{manifest['calcoli']['posizioni']}+{manifest['calcoli']['andamento']}",
            json.dumps(manifest),
            f"{BUCKET}/{manifest['versione']}/",
        ),
    )


def main(argv: list[str] | None = None) -> int:
    import psycopg

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cartella", type=Path)
    a = ap.parse_args(argv)
    with _client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"]) as c:
        manifest = pubblica(a.cartella, c)
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        registra(conn, manifest)
    print(f"Pubblicato il pacchetto {manifest['versione']} in {BUCKET}/{manifest['versione']}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
