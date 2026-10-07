# ADR 0034 — Adattamento del modello al dominio politico italiano

**Stato:** Proposto
**Dettaglia:** ADR 0031

## Contesto
I checkpoint base di Laya, sul benchmark di decisioni tipizzate, si collocano sotto la baseline della classe maggioritaria, mentre la versione adattata a quei flussi supera il riferimento commerciale. Il messaggio è chiaro: su decisioni tipizzate di dominio, la capacità viene dall'adattamento. Il dominio qui è particolare due volte, perché è politico e perché è italiano, cioè servito dal checkpoint più debole.

## Decisione
**Prima si misura, poi si adatta.** Si valuta il checkpoint multilingue sul golden set italiano (ADR 0033). Se la qualità è sufficiente per stadio, si resta zero-shot. L'adattamento si avvia solo per gli stadi che non raggiungono la soglia.

**Priorità.** Gli stadi in cui l'adattamento conta di più sono il posizionamento sugli enunciati e la classificazione per tema; il filtro di perimetro e la validazione delle citazioni sono compiti più semplici e probabilmente adeguati senza adattamento.

**Dati di addestramento.** Solo claim e voti italiani etichettati secondo la stessa tassonomia della produzione, con partizionamento per fonte e per periodo, in modo che la valutazione non misuri memorizzazione. Nessun dato proveniente dalle conversazioni degli utenti, in nessun caso (ADR 0013).

**Rischio di bias indotto.** Un modello adattato eredita il bias delle etichette. Perciò: etichettatura secondo le regole scritte, bilanciamento degli esempi per schieramento, e le stesse metriche di simmetria dell'ADR 0006 applicate al checkpoint adattato prima della promozione. Un modello adattato che migliora l'accuratezza ma peggiora la simmetria non va in produzione.

**Promozione.** Il checkpoint adattato è una configurazione candidata del laboratorio (ADR 0016) e si promuove con le stesse regole: qualità, calibrazione e simmetria.

**Pubblicazione.** Il checkpoint adattato, le etichette e la procedura vengono pubblicati, coerentemente con l'ADR 0012. Un modello che decide su materia politica e non è ispezionabile contraddirebbe il progetto.

**Nessun adattamento sul giudizio di merito.** Si adatta ciò che è classificazione e posizionamento. Non si addestra nulla che produca verdetti di verità o giudizi di valore: quelli restano confronti deterministici con fonti ufficiali (ADR 0014).

## Alternative considerate
Adattare subito, prima di misurare: scartato, si rischia di risolvere un problema che non c'è e di introdurne uno nuovo. Restare zero-shot in ogni caso: scartato, i dati suggeriscono che su questo tipo di compito la qualità arrivi dall'adattamento.

## Conseguenze
Serve capacità di addestramento occasionale, realizzabile su GPU a noleggio o su notebook gratuiti, non in continuo. Ogni versione del checkpoint va calibrata di nuovo e registrata. L'adattamento aumenta la dipendenza dalla qualità delle etichette, che diventa il vincolo principale.
