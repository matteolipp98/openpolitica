# ADR 0024 — Fasi di rilascio e perimetro dell'MVP

**Stato:** Proposto

## Contesto
Gli ADR descrivono un sistema completo che nessuno costruisce in un colpo solo. Serve un ordine che porti presto qualcosa di usabile e che non richieda di rifare le fondamenta a ogni fase.

## Decisione
**Il nucleo non usa LLM.** Enunciati curati, voti nominali e calcolo deterministico dell'affinità sono già un prodotto completo e difendibile. Gli LLM servono per scalare su notizie, fact-checking e conversazione, non per il nucleo. Il calcolo dell'affinità non cambia dalla fase 0 in poi.

**Perimetro iniziale.** Circa 10 leader e i partiti principali, 30 enunciati, 6 temi, una legislatura di voti, 20 indicatori statistici.

**Fase 0, nucleo votabile.** Import dei voti, catalogo degli enunciati, mappatura voto-enunciato, questionario, affinità nel browser, pagine partito e politico con le evidenze.

**Fase 1, programmi.** Estrazione strutturata delle promesse e schede secondo l'ADR 0020, incluso il confronto con i programmi dal 2018. Corpus finito, nessuna ingestion continua.

**Fase 2, dichiarazioni.** Ingestion RSS e GDELT, screening, estrazione claim, timeline per politico.

**Fase 3, fact-checking.** Catalogo indicatori, connettori ISTAT ed Eurostat, confronto deterministico, backoffice di revisione, statistiche aggregate dell'ADR 0019.

**Fase 4, assistente.** Intervista guidata, spiegazioni ancorate, validazione delle frasi.

**Fase 5, laboratorio.** Dataset, runner multi-modello, metriche, cruscotto pubblico di bias.

Ogni fase è rilasciabile da sola. Le fasi successive aggiungono evidenze allo stesso modello dati, senza modificare quanto già pubblicato.

**Fuori dall'MVP.** Audio e video, social senza API gratuite, collegi e candidati, elezioni diverse dalle politiche, stime di costo proprie, grafo dedicato, più di due famiglie di modelli generativi.

## Alternative considerate
Partire dalla chat, che è la parte più visibile: scartato, poggia su dati che non esistono ancora e produrrebbe risposte non ancorate. Partire dall'ingestion di notizie: scartato, è il flusso più fragile e il meno utile da solo.

## Conseguenze
Il prodotto è utile già alla fase 0, prima di qualunque spesa in modelli. Le fasi 1 e 3 sono quelle che richiedono più lavoro umano di revisione, e vanno pianificate con quel collo di bottiglia in mente.
