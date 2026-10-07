# ADR 0035 — Progettazione delle domande tipizzate

**Stato:** Proposto
**Dettaglia:** ADR 0031

## Contesto
Le domande tipizzate non sono prompt liberi: la loro forma incide sull'esito in modi misurabili. Due effetti contano in modo particolare per questo progetto.

Il primo è la **posizione delle opzioni**: a parità di testo, l'opzione che occupa il primo posto riceve un vantaggio sistematico. In un'app che classifica posizioni politiche, l'ordine in cui si elencano le opzioni diventerebbe una fonte di bias invisibile.

Il secondo è il **budget di opzioni**: le opzioni di una domanda condividono un numero fisso di token. Oltre una ventina di opzioni le etichette vengono troncate e diventano indistinguibili, e su spazi di etichette molto ampi la qualità crolla.

## Decisione
**Rotazione dell'ordine delle opzioni.** Ogni domanda di tipo `choice` o `score` che alimenta un dato pubblicato viene posta in più rotazioni, in modo che ogni opzione occupi ogni posizione lo stesso numero di volte, e le probabilità vengono mediate. Poiché tutte le domande di una richiesta condividono un unico forward pass, il costo è una frazione di riga e non una chiamata in più. La quota di risposte che cambiano con l'ordine è una metrica monitorata.

**Pochi temi per domanda.** La tassonomia dei temi resta sotto la ventina di opzioni per domanda. Se l'insieme cresce, si procede in due passaggi: una prima domanda a grana grossa, poi una domanda ristretta al sottoinsieme pertinente.

**Criteri espliciti.** Ogni opzione porta una descrizione breve e distintiva; ogni livello di una `score` ha una descrizione. Etichette lunghe o simili tra loro vanno riscritte, perché il troncamento le rende equivalenti per il modello.

**Scale ordinali coerenti.** La scala delle posizioni usa gli stessi livelli ovunque, con descrizioni fisse, così che i valori siano confrontabili tra enunciati e nel tempo.

**Domande come dati versionati.** Le domande tipizzate vivono nel repository come gli enunciati e la tassonomia (ADR 0025), con la loro versione registrata nei run.

**Simmetria delle formulazioni.** Per gli stadi che toccano posizioni politiche valgono anche i test di polarità e sensibilità dell'ADR 0030, applicati qui alla formulazione delle domande oltre che a quella degli enunciati.

## Alternative considerate
Ordine fisso delle opzioni: più semplice e più veloce, ma introduce un vantaggio posizionale che in questo dominio non è accettabile. Una sola domanda con tutte le etichette possibili: scartata per il limite di budget.

## Conseguenze
Più righe per richiesta e qualche millisecondo in più, in cambio di una fonte di bias eliminata e misurata. La tassonomia dei temi va tenuta deliberatamente piccola, il che è coerente con il perimetro dell'MVP.
