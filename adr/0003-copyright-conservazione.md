# ADR 0003 — Diritto d'autore e politica di conservazione dei contenuti

**Stato:** Proposto

## Contesto
Gli articoli giornalistici sono protetti dal diritto d'autore e dai diritti degli editori di giornali introdotti dalla Direttiva UE 2019/790 e recepiti nella legge italiana sul diritto d'autore. L'eccezione per text and data mining consente l'analisi automatizzata salvo riserva espressa dal titolare. Un'applicazione pubblica che ripubblica testi integrali sarebbe esposta.

## Decisione
Il testo integrale degli articoli di livello C viene processato in memoria o conservato solo temporaneamente per l'estrazione, poi eliminato. Si persistono metadati, URL, data, testata, i claim estratti e una citazione breve e letterale della dichiarazione del politico, necessaria come prova. L'utente viene sempre rimandato alla fonte originale.

Il crawler rispetta robots.txt e i meccanismi di opt-out per il text and data mining. Le fonti istituzionali e i documenti pubblici dei politici possono essere conservati integralmente.

## Alternative considerate
Conservazione integrale per riproducibilità: scartata per rischio legale. Accordi di licenza con editori: da valutare in una fase successiva se il progetto cresce.

## Conseguenze
La riproducibilità completa è garantita per le fonti A e B, parziale per le fonti C: il claim estratto e la citazione restano, il contesto dell'articolo no. Serve un parere legale prima del lancio pubblico.
