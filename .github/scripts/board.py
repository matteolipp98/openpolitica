"""Tiene la board del GitHub Project allineata alle issue (CLAUDE.md, "Board e flusso di lavoro").

Colonna (campo Status) decisa dalle etichette: `stato` (lo stato condiviso) e `in-corso` → In Progress,
issue chiusa → Done, il resto → Todo.
Uso:
  python board.py evento   # in un workflow `issues`: allinea l'issue dell'evento (GITHUB_EVENT_PATH)
  python board.py tutte    # allinea tutte le issue del repository
Variabili: PROJECT_TOKEN (permesso Projects), GITHUB_TOKEN, GITHUB_REPOSITORY, PROGETTO (titolo, default "openpolitica").
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request

API = "https://api.github.com"
COLONNE = {"fatto": ["done", "fatto", "completato"], "in-corso": ["in progress", "in corso"], "da-fare": ["todo", "da fare"]}


def colonna(issue: dict) -> str:
    """Stato della board per un'issue: 'fatto', 'in-corso' o 'da-fare'."""
    etichette = {(e["name"] if isinstance(e, dict) else e) for e in issue.get("labels", [])}
    if "stato" in etichette:  # l'issue con lo stato condiviso resta sempre in vista
        return "in-corso"
    if issue.get("state") == "closed":
        return "fatto"
    return "in-corso" if "in-corso" in etichette else "da-fare"


def _richiesta(url: str, token: str, dati: dict | None = None) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(dati).encode() if dati is not None else None,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "User-Agent": "op-board"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def graphql(token: str, query: str, **variabili) -> dict:
    r = _richiesta(f"{API}/graphql", token, {"query": query, "variables": variabili})
    if r.get("errors"):
        raise SystemExit(f"GraphQL: {r['errors']}")
    return r["data"]


def progetto(token: str, proprietario: str, titolo: str) -> tuple[str, str, dict[str, str]]:
    """(id del progetto, id del campo Status, {colonna: id dell'opzione})."""
    q = """query($login: String!) { repositoryOwner(login: $login) { ... on ProjectV2Owner {
      projectsV2(first: 50) { nodes { id title field(name: "Status") {
        ... on ProjectV2SingleSelectField { id options { id name } } } } } } } }"""
    nodi = graphql(token, q, login=proprietario)["repositoryOwner"]["projectsV2"]["nodes"]
    scelti = [n for n in nodi if n["title"].strip().lower() == titolo.lower()] or nodi[:1]
    if not scelti or not scelti[0].get("field"):
        raise SystemExit(f"Nessun progetto '{titolo}' con un campo Status per {proprietario}")
    p = scelti[0]
    opzioni = {}
    for chiave, nomi in COLONNE.items():
        for o in p["field"]["options"]:
            if o["name"].strip().lower() in nomi:
                opzioni[chiave] = o["id"]
    mancanti = set(COLONNE) - set(opzioni)
    if mancanti:
        raise SystemExit(f"Colonne non trovate nella board: {mancanti}; ci sono {[o['name'] for o in p['field']['options']]}")
    return p["id"], p["field"]["id"], opzioni


def allinea(token: str, prog: tuple[str, str, dict[str, str]], issue: dict) -> str:
    pid, campo, opzioni = prog
    item = graphql(
        token,
        "mutation($p: ID!, $c: ID!) { addProjectV2ItemById(input: {projectId: $p, contentId: $c}) { item { id } } }",
        p=pid, c=issue["node_id"],
    )["addProjectV2ItemById"]["item"]["id"]  # fmt: skip
    col = colonna(issue)
    graphql(
        token,
        """mutation($p: ID!, $i: ID!, $f: ID!, $o: String!) { updateProjectV2ItemFieldValue(input:
           {projectId: $p, itemId: $i, fieldId: $f, value: {singleSelectOptionId: $o}}) { projectV2Item { id } } }""",
        p=pid, i=item, f=campo, o=opzioni[col],
    )  # fmt: skip
    return col


def main() -> int:
    token = os.environ["PROJECT_TOKEN"]
    repo = os.environ["GITHUB_REPOSITORY"]
    prog = progetto(token, repo.split("/")[0], os.environ.get("PROGETTO", "openpolitica"))
    if sys.argv[1:] == ["evento"]:
        evento = json.load(open(os.environ["GITHUB_EVENT_PATH"], encoding="utf8"))
        issue = evento["issue"]
        print(f"#{issue['number']} → {allinea(token, prog, issue)}")
        return 0
    gh = os.environ.get("GITHUB_TOKEN", token)
    pagina = 1
    while True:
        issues = _richiesta(f"{API}/repos/{repo}/issues?state=all&per_page=100&page={pagina}", gh, None)
        if not issues:
            return 0
        for i in issues:
            if "pull_request" not in i:
                print(f"#{i['number']} → {allinea(token, prog, i)}")
        pagina += 1


if __name__ == "__main__":
    sys.exit(main())
