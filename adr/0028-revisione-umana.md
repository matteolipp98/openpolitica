# ADR 0028 — Capacità di revisione umana e regole di pubblicazione

**Stato:** Proposto, modificato da ADR 0030 (nessun verdetto pubblicato finché non c'è revisione)
**Dettaglia:** ADR 0004 stadio 7

## Contesto
Più ADR prevedono revisione umana obbligatoria e la indicano come collo di bottiglia, senza dire chi rivede, quanto e cosa succede se la coda cresce. Per un progetto portato avanti da poche persone questa è la variabile che determina il ritmo reale di pubblicazione.

## Decisione
**Cosa richiede revisione prima della pubblicazione.** Gli esiti "contraddetto" e "fuorviante per contesto" (ADR 0014); le posizioni pubblicate che derivano da dichiarazioni anziché da voti (ADR 0008); la mappatura voto-enunciato e il catalogo degli enunciati (ADR 0022); le schede delle promesse (ADR 0020); i contenuti in coda di ispezione (ADR 0026, 0027).

**Cosa si pubblica senza revisione.** I dati istituzionali importati, cioè voti, atti e resoconti; i claim archiviati come dichiarazioni con citazione e link, senza alcun giudizio; gli esiti "supportato" e "non verificabile", con campionamento casuale a posteriori.

**Regola di coda.** Ciò che attende revisione non viene pubblicato: resta invisibile, non appare come "in verifica" accanto al soggetto, per non trasformare un arretrato in un segnale implicito.

**Priorità.** Prima le schede delle promesse in periodo elettorale, poi gli esiti negativi più recenti, poi il resto. In modalità campagna la revisione è rafforzata e la metodologia è congelata (ADR 0021).

**Qualità della revisione.** Doppia revisione indipendente per gli esiti "contraddetto"; disaccordo risolto dal panel. Ogni decisione registra revisore, data e motivazione, e resta storicizzata (ADR 0005). I revisori non rivedono soggetti verso cui hanno un conflitto di interessi dichiarato.

**Composizione.** Almeno due revisori di orientamenti dichiaratamente diversi sugli esiti negativi. È un requisito di simmetria, non di gusto: una revisione monocolore invaliderebbe l'intero impianto anti-bias.

**Dimensionamento.** Il volume atteso di esiti negativi guida il perimetro: se la coda cresce oltre la capacità, si riduce il numero di politici monitorati o la finestra temporale, non si allentano i criteri di pubblicazione.

## Alternative considerate
Pubblicazione automatica con correzione a posteriori: scartata per il rischio diffamatorio. Revisione affidata a volontari aperti: interessante per la scala, ma richiede un processo di qualità e di conflitto di interessi che oggi non esiste; rimandata.

## Conseguenze
Il ritmo di pubblicazione è vincolato dalle persone disponibili, ed è una scelta esplicita. Il perimetro dell'MVP (10 politici) è dimensionato su questa capacità.
