"""Crea (o trova) su Render il cron job che importa ogni notte i voti di Camera e Senato (ADR 0017).

Usa la API di Render con RENDER_API_KEY. Se Render non ha accesso al repository GitHub,
la creazione fallisce con un messaggio: va collegato una volta dalla dashboard di Render.
"""

import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.render.com/v1"
NOME = "openpolitica-import-voti"
REPO = "https://github.com/matteolipp98/openpolitica"
RAMO = os.environ.get("GITHUB_REF_NAME", "main")
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
        return e.code, e.read().decode(errors="replace")


def main() -> int:
    stato, owners = api("GET", "/owners?limit=20")
    if stato != 200 or not owners:
        scrivi(f"Render: chiave non valida o nessun account (HTTP {stato}): {owners}")
        return 1
    owner = owners[0]["owner"]
    scrivi(f"Render: account **{owner.get('name')}** ({owner['id']})")

    stato, servizi = api("GET", f"/services?name={NOME}&limit=20")
    esistente = None
    if stato == 200:
        esistente = next((s["service"] for s in servizi if s["service"]["name"] == NOME), None)

    env = [{"key": "PYTHONUNBUFFERED", "value": "1"}]
    if os.environ.get("DB"):
        env.append({"key": "DATABASE_URL", "value": os.environ["DB"]})

    if esistente:
        scrivi(f"Job già presente: {esistente['id']} {esistente.get('dashboardUrl', '')}")
        if os.environ.get("DB"):
            stato, _ = api("PUT", f"/services/{esistente['id']}/env-vars", env)
            scrivi(f"Variabili aggiornate: HTTP {stato}")
        return 0

    stato, risposta = api(
        "POST",
        "/services",
        {
            "type": "cron_job",
            "name": NOME,
            "ownerId": owner["id"],
            "repo": REPO,
            "branch": RAMO,
            "rootDir": "workers",
            "autoDeploy": "yes",
            "envVars": env,
            "serviceDetails": {
                "env": "python",
                "region": "frankfurt",
                "plan": "starter",
                "schedule": "17 3 * * *",
                "envSpecificDetails": {
                    "buildCommand": "pip install uv && uv sync --frozen",
                    "startCommand": "uv run python -m op_workers.connettori.importa_voti camera && "
                    "uv run python -m op_workers.connettori.importa_voti senato",
                },
            },
        },
    )
    if stato in (200, 201):
        s = risposta.get("service", risposta)
        scrivi(f"Job creato: {s.get('id')} {s.get('dashboardUrl', '')}")
        if not os.environ.get("DB"):
            scrivi("Attenzione: manca DATABASE_URL (secret SUPABASE_DB_URL): il job fallirà finché non viene aggiunta.")
        return 0
    scrivi(f"Render: creazione non riuscita (HTTP {stato}): {risposta}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
