"""Collega il web service Docker di Render al database: imposta DATABASE_URL e fa ripartire il servizio.

Trova il servizio collegato a questo repository con la API di Render (RENDER_API_KEY).
Il valore viene dal secret SESSION_POOLER e non viene mai stampato.
"""

import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.render.com/v1"
REPO = "github.com/matteolipp98/openpolitica"
RIEPILOGO = os.environ.get("GITHUB_STEP_SUMMARY")


def scrivi(msg: str) -> None:
    print(msg)
    if RIEPILOGO:
        with open(RIEPILOGO, "a") as f:
            f.write(msg + "\n\n")


def api(metodo: str, percorso: str, corpo=None):
    req = urllib.request.Request(
        API + percorso,
        method=metodo,
        data=json.dumps(corpo).encode() if corpo is not None else None,
        headers={
            "Authorization": f"Bearer {os.environ['RENDER_API_KEY']}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:500]


def main() -> int:
    db = os.environ.get("DB", "")
    if not db:
        scrivi("Manca il secret SESSION_POOLER: niente da collegare.")
        return 1
    stato, servizi = api("GET", "/services?limit=50")
    if stato != 200:
        scrivi(f"Render: elenco servizi non riuscito (HTTP {stato}): {servizi}")
        return 1
    nostri = [s["service"] for s in servizi if REPO in (s["service"].get("repo") or "")]
    if not nostri:
        scrivi("Render: nessun servizio collegato al repository. Servizi visti: "
               + ", ".join(s["service"]["name"] for s in servizi))
        return 1
    for s in nostri:
        stato, _ = api("PUT", f"/services/{s['id']}/env-vars/DATABASE_URL", {"value": db})
        scrivi(f"Render: **{s['name']}** ({s['type']}, branch {s.get('branch')}): DATABASE_URL impostata, HTTP {stato}")
        if stato in (200, 201):
            stato, _ = api("POST", f"/services/{s['id']}/deploys", {"clearCache": "do_not_clear"})
            scrivi(f"Render: nuovo deploy avviato, HTTP {stato}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
