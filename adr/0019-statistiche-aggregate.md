# ADR 0019 — Statistiche aggregate e regola del denominatore

**Stato:** Proposto, modificato da ADR 0037 (pubblicazione da subito e letture comparative); ADR 0039 (quattro indicatori su promesse e annunci) e 0040 (serie nel tempo)
**Precisa:** ADR 0009

## Contesto
Servono statistiche del tipo "quante cose scorrette dice", perché sono ciò che un elettore cerca. Sono anche la parte più attaccabile: se qualcuno sceglie quali affermazioni verificare, la percentuale misura la selezione e non il politico. Chi parla molto ha molti claim verificati; chi parla in modo vago non ha claim verificabili e appare impeccabile.

L'ADR 0009 vieta i punteggi sintetici. Questo ADR chiarisce che le statistiche descrittive sono invece ammesse, a condizioni precise.

## Decisione
**Regola del denominatore.** Una percentuale è pubblicabile solo se la popolazione dei claim è selezionata meccanicamente e in modo identico per tutti i soggetti: tutti i claim di un tipo, estratti dalle fonti monitorate, in una finestra temporale definita. Nessuna selezione editoriale, nessun "claim più significativi".

**Metriche pubblicate.** Il tasso di imprecisione sui claim quantitativi verificabili. Il tasso di non verificabilità, cioè la quota di affermazioni che non sono controllabili, indicatore autonomo e informativo. La coerenza tra dichiarazioni e voti. Lo stato delle promesse, distinto in mantenute, parziali e non mantenute. Il volume di dichiarazioni, come contesto indispensabile.

**Presentazione.** Ogni percentuale mostra sempre numeratore, denominatore, finestra temporale e intervallo di confidenza. Sotto una soglia minima di claim la percentuale non viene mostrata, solo il conteggio assoluto. Le statistiche sono confrontabili tra soggetti solo a parità di finestra e di fonti, e l'interfaccia lo impone.

**Normalizzazione per ruolo.** Le promesse si valutano tenendo conto che l'opposizione non può attuare: si confronta con chi era nella stessa posizione, e questo va dichiarato accanto al dato.

**Niente indice sintetico.** Nessuna fusione delle metriche in un unico punteggio di affidabilità: il peso relativo tra un numero sbagliato e una promessa tradita è una scelta di valore, e il prodotto non ne fa (ADR 0001).

**Asimmetrie.** Se le statistiche mostrano differenze sistematiche tra schieramenti, queste vengono pubblicate insieme all'audit di copertura delle fonti (ADR 0006), così che il lettore possa distinguere un effetto reale da un effetto del campione.

## Alternative considerate
Un punteggio unico di affidabilità: scartato. Verifica dei soli claim più virali: scartato perché rompe la regola del denominatore, resta possibile come vista separata e dichiarata, senza percentuali.

## Conseguenze
Nei primi mesi i denominatori saranno piccoli e molte percentuali resteranno nascoste: è corretto e va spiegato nell'interfaccia. Il tasso di non verificabilità diventerà probabilmente il dato più citato del prodotto.
