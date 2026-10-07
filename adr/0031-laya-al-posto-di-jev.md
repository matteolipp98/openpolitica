# ADR 0031 — Laya al posto di Jev come motore di decisione

**Stato:** Proposto, usato dall'ADR 0039 per gli indicatori su promesse e annunci
**Sostituisce:** ADR 0018

## Contesto
L'ADR 0018 affidava a Jev (TypeSafe AI) gli stadi di decisione della pipeline. Jev è un servizio chiuso, a pagamento, con accesso su lista d'attesa, e riceve anche le risposte degli utenti nella chat.

Laya è un motore di decisione System 1 non autoregressivo con licenza Apache 2.0. Espone gli stessi tre primitivi — `choice`, `score`, `noul` — risponde a tutte le domande di una richiesta in un singolo forward pass senza generare testo, e parla lo stesso protocollo HTTP di Jev su `POST /v1/systemone`, quindi la sostituzione non cambia lo schema delle chiamate. Ha tre checkpoint: inglese, multilingue (100+ lingue) e uno specializzato sulle decisioni tipizzate, con un router che sceglie quello giusto per lingua.

## Decisione
Laya sostituisce Jev in tutti i punti previsti dall'ADR 0018: filtro di perimetro, classificazione dei claim, posizionamento sugli enunciati, validazione delle citazioni e guardrail della chat. I primitivi e la forma delle domande restano gli stessi, quindi gli altri ADR non cambiano nel merito.

**Perché.** I pesi sono aperti, quindi il modello si può eseguire in proprio, ispezionare, misurare e adattare al dominio. Nessun token esce verso un fornitore terzo: le risposte degli utenti nella chat restano sull'infrastruttura del progetto, il che semplifica molto i vincoli dell'ADR 0013. Il costo diventa calcolo e non consumo. Non c'è lista d'attesa e non c'è un fornitore che può cambiare condizioni o ritirare l'accesso.

**Per il progetto conta soprattutto una cosa:** un modello di decisione chiuso è un giudice non ispezionabile dentro un sistema che si propone di misurare il bias. Con pesi aperti, il modello che decide è analizzabile quanto il resto.

**Italiano.** Il testo italiano viene instradato al checkpoint multilingue. Questo ha due implicazioni che non vanno sottovalutate: l'accuratezza multilingue è sensibilmente inferiore a quella inglese, e il checkpoint multilingue viene distribuito senza temperature calibrate. Prima di qualunque uso in produzione valgono gli ADR 0032 e 0033.

**Qualità zero-shot.** Sul benchmark di decisioni tipizzate i checkpoint base si collocano sotto la baseline della classe maggioritaria, mentre la versione specializzata supera nettamente Jev. La capacità, su questo tipo di compito, viene dall'adattamento al dominio: vedi ADR 0034.

**Fallback.** Se su dati italiani del dominio Laya non raggiunge una qualità accettabile rispetto al golden set, lo stadio ricade su un LLM generativo a output strutturato, più costoso e più lento, senza cambiare lo schema dati. La decisione di adottarlo in produzione è subordinata alla valutazione dell'ADR 0033.

## Alternative considerate
Restare su Jev: scartato per costo, dipendenza e opacità. Usare entrambi e confrontarli: resta possibile nel laboratorio (ADR 0016), non in produzione.

## Conseguenze
Il progetto si prende in carico l'esecuzione del modello (ADR 0032), la sua calibrazione (0033) e il suo adattamento (0034). In cambio ottiene costo marginale nullo per decisione, nessun dato verso terzi e un componente ispezionabile.
