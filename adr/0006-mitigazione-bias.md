# ADR 0006 — Strategia misurabile di mitigazione del bias

**Stato:** Proposto, esteso da ADR 0016

## Contesto
Gli LLM hanno bias politici documentati, e il bias può entrare anche da fonti, tassonomia, scelta dei temi e revisori umani. Dichiarare neutralità non è sufficiente né credibile: il bias va misurato.

## Decisione
Si adottano sei meccanismi, ciascuno con una metrica pubblicata.

**Anonimizzazione.** Prima degli stadi di valutazione nome, partito, riferimenti a coalizioni e indizi identificativi vengono sostituiti da segnaposto. Metrica: tasso di re-identificazione con un classificatore avversario.

**Test controfattuale.** Ogni claim di un campione viene rivalutato attribuendolo a speaker di schieramenti diversi. Metrica: differenza negli esiti per schieramento, con soglia di allarme.

**Ensemble multi-famiglia.** Più famiglie di modelli diverse per classificazione e verifica, con obiettivo di almeno tre (vedi la questione aperta nell'ADR 0016). Il disaccordo non viene mediato ma mostrato come incertezza. Metrica: accordo tra modelli per schieramento dello speaker.

**Golden set umano bilanciato.** Annotatori di orientamenti diversi etichettano un campione stratificato. Metriche: accordo tra annotatori e calibrazione dei modelli rispetto al consenso umano.

**Audit di copertura.** Monitoraggio di quanti claim, verifiche ed esiti negativi riguardano ciascuno schieramento, normalizzati per volume di dichiarazioni. Una disparità non è automaticamente un bias, ma va spiegata.

**Simmetria editoriale.** Tassonomia dei temi ed enunciati del questionario vengono revisionati da un panel pluralista (vedi ADR 0012).

## Alternative considerate
Un unico modello "allineato alla neutralità": scartato perché non verificabile. Solo revisione umana: scartata per costo e perché anche gli umani hanno bias.

## Conseguenze
Serve una suite di valutazione continua che giri a ogni cambio di modello o di prompt, e un cruscotto pubblico con le metriche. Un cambio di modello che peggiora le metriche di simmetria blocca il rilascio. Le misurazioni comparative tra modelli e la promozione delle configurazioni in produzione sono definite nell'ADR 0016.
