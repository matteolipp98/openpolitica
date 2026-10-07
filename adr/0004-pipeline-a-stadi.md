# ADR 0004 — Pipeline agentica a stadi con responsabilità strette

**Stato:** Proposto

## Contesto
Un singolo agente che legge, interpreta e giudica concentra tutti i bias in un punto non ispezionabile. Serve una pipeline in cui ogni passaggio sia verificabile separatamente.

## Decisione
La pipeline è composta da stadi indipendenti, ciascuno con input e output validati da uno schema.

1. **Estrazione dei claim.** Un agente estrae affermazioni atomiche con speaker, data, citazione letterale e riferimento alla fonte. Non valuta nulla. Un controllo deterministico verifica che la citazione compaia davvero nel testo sorgente.
2. **Risoluzione delle entità.** Collegamento dello speaker all'anagrafica e deduplicazione con claim già noti, secondo le regole dell'ADR 0027: in caso di ambiguità il claim resta non attribuito.
3. **Classificazione.** Tipo di claim (fattuale, promessa, previsione, giudizio di valore, attacco personale) e tema da una tassonomia fissa e versionata.
4. **Verifica fattuale.** Solo per i claim fattuali: retrieval su fonti istituzionali (ISTAT, Eurostat, Banca d'Italia, UPB, Ragioneria dello Stato). Esiti possibili: supportato, contraddetto, impreciso, non verificabile. Un esito diverso da "non verificabile" richiede almeno una fonte citata.
5. **Tracciamento delle promesse.** Collegamento delle promesse ad atti successivi: proposte di legge, emendamenti, voti.
6. **Estrazione delle posizioni.** Mappatura di voti e dichiarazioni sugli enunciati del questionario valoriale (vedi ADR 0008).
7. **Revisione umana.** Campionamento casuale e revisione obbligatoria per gli esiti "contraddetto", prima della pubblicazione; perimetro, priorità e regole di coda nell'ADR 0028.

Gli stadi 3-6 operano su claim anonimizzati (vedi ADR 0006). L'orchestrazione è deterministica: gli LLM operano dentro stadi definiti, non decidono il flusso.

## Alternative considerate
Un agente autonomo con tool: scartato per scarsa verificabilità e comportamento non riproducibile. Pipeline senza revisione umana: scartata per rischio di diffamazione.

## Conseguenze
Maggiore costo di inferenza e latenza, compensati da auditabilità e dalla possibilità di valutare ogni stadio con metriche proprie. Il collo di bottiglia operativo diventa la revisione umana, da dimensionare in base al volume.
