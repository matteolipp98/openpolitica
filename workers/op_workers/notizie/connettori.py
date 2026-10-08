"""Connettori dei documenti (piano §5.1): dal contenuto scaricato all'elenco degli elementi da leggere.

Funzioni pure sui byte, così i test non escono in rete. Il download e le regole di cortesia sono in rete.py.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import quote, urljoin

import feedparser
import lxml.etree
import lxml.html
import trafilatura

from op_workers.notizie.rete import normalizza_url
from op_workers.notizie.testo import pulisci

GDELT = "https://api.gdeltproject.org/api/v2/doc/doc"
MAX_GDELT = 250  # il massimo che la DOC API restituisce in una risposta


class ErroreFonte(RuntimeError):
    """La fonte ha risposto con qualcosa che non è quello che ci aspettiamo."""


@dataclass
class Elemento:
    url: str
    titolo: str | None = None
    pubblicato_il: datetime | None = None
    sommario: str | None = None  # quello che dà il feed: si usa per il primo filtro sui nomi
    testo: str | None = None  # già completo (Telegram): non serve scaricare la pagina
    dominio: str | None = None  # testata dell'articolo (GDELT)


def _data(x) -> datetime | None:
    if not x:
        return None
    if isinstance(x, datetime):
        return x if x.tzinfo else x.replace(tzinfo=UTC)
    s = str(x).strip()
    for prova in (
        lambda: datetime.fromisoformat(s.replace("Z", "+00:00")),
        lambda: parsedate_to_datetime(s),
        lambda: datetime.strptime(s, "%Y%m%dT%H%M%SZ"),
    ):
        try:
            d = prova()
        except (ValueError, TypeError):
            continue
        return d if d.tzinfo else d.replace(tzinfo=UTC)
    return None


def _testo_html(frammento: str) -> str:
    if not frammento or not frammento.strip():
        return ""
    try:
        return pulisci(lxml.html.fromstring(frammento).text_content())
    except (lxml.etree.ParserError, ValueError):
        return pulisci(frammento)


def _sommario(e) -> str | None:
    """Il testo più lungo che il feed dà: il contenuto intero (content:encoded) se c'è, altrimenti il sommario."""
    testi = [_testo_html(c.get("value", "")) for c in e.get("content", [])] + [_testo_html(e.get("summary", ""))]
    return max(testi, key=len) or None


def da_rss(contenuto: bytes) -> list[Elemento]:
    feed = feedparser.parse(contenuto)
    if feed.bozo and not feed.entries:
        raise ErroreFonte(f"feed illeggibile: {feed.get('bozo_exception')!r}"[:200])
    out = []
    for e in feed.entries:
        if not e.get("link"):
            continue
        quando = e.get("published") or e.get("updated")
        out.append(
            Elemento(
                url=normalizza_url(e.link),
                titolo=pulisci(e.get("title")) or None,
                pubblicato_il=_data(quando),
                sommario=_sommario(e),
            )
        )
    return out


def da_sito(contenuto: bytes, url_pagina: str, link: str) -> list[Elemento]:
    """Indirizzi delle notizie da una pagina d'elenco o da una sitemap, i più recenti per primi."""
    regola = re.compile(link)
    if b"<urlset" in contenuto[:2000]:
        radice = _xml(contenuto)
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        voci = [
            (u.findtext("s:loc", namespaces=ns) or "", _data(u.findtext("s:lastmod", namespaces=ns)))
            for u in radice.findall("s:url", ns)
        ]
        voci.sort(key=lambda v: v[1] or datetime.min.replace(tzinfo=UTC), reverse=True)
        return [Elemento(url=normalizza_url(u), pubblicato_il=d) for u, d in voci if regola.search(u.strip())]
    pagina = lxml.html.fromstring(contenuto)
    visti, out = set(), []
    for a in pagina.iter("a"):
        u = normalizza_url(urljoin(url_pagina, a.get("href") or ""))
        if regola.search(u) and u not in visti:
            visti.add(u)
            out.append(Elemento(url=u))
    return out


def _xml(contenuto: bytes):
    return lxml.etree.fromstring(contenuto, parser=lxml.etree.XMLParser(resolve_entities=False, no_network=True))


def figli_sitemap(contenuto: bytes, filtro: str) -> list[str]:
    """Le sitemap di un indice di sitemap il cui indirizzo contiene `filtro`."""
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = [(x.text or "").strip() for x in _xml(contenuto).findall("s:sitemap/s:loc", ns)]
    return [u for u in locs if filtro in u]


def da_telegram(contenuto: bytes) -> list[Elemento]:
    """Messaggi dall'anteprima pubblica t.me/s/<canale>: solo il testo, niente foto, audio o video."""
    pagina = lxml.html.fromstring(contenuto)
    out = []
    for m in pagina.xpath("//div[contains(@class,'tgme_widget_message ') and @data-post]"):
        corpi = m.xpath(".//div[contains(@class,'tgme_widget_message_text')]")
        if not corpi:
            continue
        for br in corpi[0].iter("br"):
            br.tail = "\n" + (br.tail or "")
        testo = pulisci(corpi[0].text_content())
        if not testo:
            continue
        quando = m.xpath(".//time/@datetime")
        prima_riga = testo.split("\n", 1)[0]
        out.append(
            Elemento(
                url=f"https://t.me/{m.get('data-post')}",
                titolo=prima_riga[:140],
                pubblicato_il=_data(quando[0]) if quando else None,
                testo=testo,
            )
        )
    return list(reversed(out))  # la pagina li mostra dal più vecchio: prima i più recenti


def url_gdelt(forme: list[str], filtro: str, ore: int) -> str:
    nomi = " OR ".join(f'"{f}"' for f in forme)
    query = f"({nomi}) {filtro}".strip()
    return f"{GDELT}?query={quote(query)}&mode=artlist&format=json&sort=datedesc&maxrecords={MAX_GDELT}&timespan={ore}h"


def da_gdelt(contenuto: bytes) -> list[Elemento]:
    try:
        dati = json.loads(contenuto or b"{}")
    except ValueError as e:
        # Quando si chiede troppo spesso GDELT risponde con una frase, non con JSON
        raise ErroreFonte(contenuto[:200].decode("utf8", "replace").strip()) from e
    return [
        Elemento(
            url=normalizza_url(a["url"]),
            titolo=pulisci(a.get("title")) or None,
            pubblicato_il=_data(a.get("seendate")),
            dominio=a.get("domain"),
        )
        for a in dati.get("articles", [])
        if a.get("url")
    ]


NASCOSTI = (
    "//*[@hidden or @aria-hidden='true' or contains(translate(@style,' ',''),'display:none')"
    " or contains(translate(@style,' ',''),'visibility:hidden')]"
)


CHARSET = re.compile(rb"""<meta[^>]+charset=["']?([A-Za-z0-9_-]+)""", re.IGNORECASE)


def decodifica(contenuto: bytes) -> str:
    """Il testo della pagina: la codifica dichiarata nella pagina, altrimenti UTF-8, altrimenti Windows-1252."""
    if m := CHARSET.search(contenuto[:4000]):
        try:
            return contenuto.decode(m.group(1).decode("ascii"), "replace")
        except LookupError:
            pass
    try:
        return contenuto.decode("utf8")
    except UnicodeDecodeError:
        return contenuto.decode("cp1252", "replace")


def estrai_pagina(contenuto: bytes, url: str) -> tuple[str | None, str | None, datetime | None]:
    """Titolo, testo principale e data di una pagina. Il testo nascosto si toglie prima (ADR 0026)."""
    html = re.sub(r"^\s*<\?xml[^>]*\?>", "", decodifica(contenuto))
    try:
        albero = lxml.html.fromstring(html)
    except (lxml.etree.ParserError, ValueError):
        return None, None, None
    for el in albero.xpath(NASCOSTI):
        if el.getparent() is not None and el.tag not in ("html", "body"):
            el.drop_tree()
    doc = trafilatura.bare_extraction(albero, url=url, with_metadata=True, include_comments=False)
    if doc is None:
        return None, None, None
    return pulisci(doc.title) or None, pulisci(doc.text) or None, _data(doc.date)
