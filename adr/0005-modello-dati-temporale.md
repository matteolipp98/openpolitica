# ADR 0005 — Modello dati temporale e tracciabilità delle fonti

**Stato:** Proposto

## Contesto
La storia pregressa è centrale: coerenza nel tempo, promesse mantenute, cambi di posizione. Le posizioni cambiano, e anche le valutazioni del sistema possono essere corrette. Serve sapere sia quando un fatto è avvenuto sia quando il sistema lo ha registrato.

## Decisione
Modello bitemporale: ogni entità ha un tempo di validità (quando la dichiarazione o il voto è avvenuto) e un tempo di registrazione (quando il sistema l'ha acquisito o rivalutato). Nessun record viene sovrascritto: le correzioni creano nuove versioni.

Entità principali: Politico (con storico di cariche e appartenenze di partito), Fonte, Documento, Claim, Voto, Atto, Promessa, Verifica, Posizione, Enunciato del questionario.

Relazioni rappresentate come grafo: un Claim deriva da un Documento, contraddice o conferma un altro Claim, una Promessa è seguita da un Atto, un Voto esprime una Posizione su un Enunciato.

Ogni Verifica registra la versione di prompt, modello, tassonomia e snapshot delle fonti usati, così da essere riproducibile.

## Alternative considerate
Modello relazionale non temporale: scartato perché perde la storia delle correzioni, che è anche una difesa legale. Solo grafo: scartato come unico storage per la complessità analitica; il grafo affianca un archivio colonnare per le analisi.

## Conseguenze
Query più complesse, ma diventano possibili timeline delle posizioni, rilevazione dei cambi di posizione, audit completo delle correzioni e pagina pubblica "cosa abbiamo corretto".
