# ADR 0032 — Esecuzione e deployment di Laya

**Stato:** Proposto
**Dettaglia:** ADR 0031

## Contesto
Con pesi aperti il modello va eseguito dal progetto. Lo stack (ADR 0017) è su Render, senza GPU gestite, e deve servire due profili di carico molto diversi: la pipeline, che è batch e tollera latenza, e la chat, che è interattiva.

I checkpoint hanno 322M parametri (multilingue) e 421M (inglese e specializzato). Su CPU una richiesta costa centinaia di millisecondi, su GPU decine.

## Decisione
**Un servizio dedicato.** `laya-serve` gira come servizio Docker su Render, separato dai worker, esponendo l'endpoint HTTP. I worker Python e le funzioni della chat lo chiamano via HTTP; nessun processo carica il modello in proprio. Autenticazione con bearer token, servizio non esposto pubblicamente.

**Checkpoint residenti.** Si precaricano i checkpoint usati, così la latenza è quella dell'inferenza e non del caricamento: un checkpoint ricaricato a ogni cambio costa secondi. Per l'italiano serve il solo checkpoint multilingue, più l'eventuale checkpoint adattato dell'ADR 0034.

**Versione fissata.** Il checkpoint è pinnato per revisione, con verifica dell'hash, e la versione è registrata in ogni run (ADR 0016). Un aggiornamento di modello è un rilascio come un altro, con le valutazioni che lo precedono.

**Batch per la pipeline.** Le decisioni della pipeline sono inviate in lotti, con raggruppamento per lunghezza: su carichi misti il risparmio è sostanziale rispetto alle chiamate una per volta. La chat usa invece chiamate singole.

**Budget di token.** Il checkpoint multilingue legge fino a 8.192 token, ma di default ne legge molti meno: per i documenti lunghi si imposta esplicitamente il limite e, dove serve, si usa la scansione a finestre, ricordando che la probabilità restituita è quella della finestra decisiva e non una misura calibrata sull'intero documento. Per la pipeline è preferibile decidere sul singolo claim, che è corto, invece che sul documento intero.

**Dimensionamento.** Istanza Render con memoria sufficiente a tenere residente un checkpoint, thread CPU limitati al numero di core fisici. Se la latenza della chat non è accettabile su CPU, le opzioni sono tre, in ordine: esportare in ONNX con quantizzazione, ridurre il numero di domande per richiesta, oppure spostare il solo servizio di inferenza su un fornitore con GPU.

**Degrado.** Se il servizio è indisponibile, la pipeline accumula in coda e la chat ricade sul questionario strutturato (ADR 0029). Il nucleo deterministico non dipende da Laya.

## Alternative considerate
Modello in-process nei worker: più semplice, ma duplica la memoria e impedisce il batch condiviso. Inferenza nel browser tramite la build JavaScript: interessante per la privacy della chat, scartata per ora per peso del download e consumo sul dispositivo; da rivalutare.

## Conseguenze
Un servizio in più da gestire e monitorare, con costo fisso invece che per token. Latenza su CPU da misurare presto con un prototipo: è il dato che decide se la chat resta su Render o se serve un nodo con GPU.
