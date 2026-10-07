# ADR 0025 — Struttura del repository e pratiche di sviluppo

**Stato:** Proposto

## Contesto
Diversi ADR impongono requisiti che si rispettano solo se il repository è organizzato di conseguenza: riproducibilità degli output, versionamento di prompt e tassonomie, pubblicazione della metodologia, separazione tra laboratorio e produzione.

## Decisione
**Monorepo** con quattro aree: l'applicazione web (Next.js su Vercel), i worker Python (ingestion, pipeline, connettori, laboratorio), i pacchetti condivisi (schema dati, tipi, algoritmo di affinità) e il contenuto metodologico.

**L'algoritmo di affinità è codice condiviso e testato**, usato dal client e dai test, con casi di riferimento fissi: stesse risposte, stesso risultato, sempre.

**Il contenuto metodologico vive nel repository come dati versionati**: enunciati, tassonomia dei temi, mappatura voto-enunciato, catalogo degli indicatori, regole di tolleranza, paniere delle fonti, perimetro dei politici, prompt. Sono file di dati con schema validato, non stringhe sparse nel codice. Ogni modifica passa da una pull request: è il modo in cui il panel rivede il contenuto e in cui la metodologia resta pubblica.

**Prompt e configurazioni di modello sono versionati** e riferiti per identificativo nelle tabelle dei run, così ogni output resta riconducibile alla versione che lo ha prodotto.

**Migrazioni del database** versionate nel repository, con dati di esempio per l'ambiente locale.

**Test.** Unitari sull'affinità e sul motore di confronto numerico; di contratto sui connettori, con risposte reali registrate, così le rotture delle fonti emergono subito; di valutazione sui dataset del laboratorio, eseguiti a ogni modifica di prompt, modello o tassonomia, con soglie che bloccano il rilascio se le metriche di simmetria peggiorano (ADR 0006).

**Ambienti.** Locale con database Supabase di sviluppo, staging e produzione. Nessun dato reale di conversazione in nessun ambiente (ADR 0013).

**Licenza e apertura.** Codice e contenuto metodologico pubblici. I dati derivati pubblicati con licenza aperta, nel rispetto dei vincoli delle fonti (ADR 0003).

**Segreti** solo nelle variabili d'ambiente delle piattaforme; le chiavi dei fornitori di modelli stanno solo nel gateway LiteLLM, mai nell'app web.

## Alternative considerate
Repository separati per app e pipeline: più pulito ma rende faticoso mantenere allineati schema e algoritmo di affinità. Contenuto metodologico in database anziché nel repository: perde la revisione tramite pull request, che qui è un requisito di governance.

## Conseguenze
Le modifiche metodologiche diventano più lente e più tracciabili, che è l'effetto voluto. Il repository pubblico espone la metodologia a critiche: è una scelta dichiarata nell'ADR 0012.
