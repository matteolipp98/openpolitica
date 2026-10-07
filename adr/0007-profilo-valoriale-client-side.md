# ADR 0007 — Profilo valoriale dell'utente calcolato lato client

**Stato:** Proposto, modificato da ADR 0013 (elaborazione effimera della conversazione) e ADR 0037 (importanza per domanda al posto dei pesi per tema)

## Contesto
Per valutare i politici secondo il proprio credo etico l'utente deve esprimere posizioni e priorità. Queste informazioni sono opinioni politiche e convinzioni personali, cioè categorie particolari di dati ai sensi dell'art. 9 del GDPR. Un database centralizzato di opinioni politiche dei cittadini sarebbe un rischio grave di sicurezza, di abuso e di reputazione.

## Decisione
Il profilo valoriale non lascia mai il dispositivo dell'utente per impostazione predefinita. Il questionario, il profilo e il calcolo delle affinità avvengono lato client: il server fornisce solo i dati pubblici delle posizioni dei politici, identici per tutti.

La persistenza è locale. Una sincronizzazione tra dispositivi, se richiesta, avviene solo con cifratura end-to-end e consenso esplicito. Nessuna analitica associa risposte a identificativi. Eventuali statistiche aggregate usano tecniche di privacy differenziale e opt-in esplicito.

L'utente può esprimere il credo etico a due livelli: posizioni su enunciati concreti ("sono favorevole a...") e pesi sui temi che considera prioritari. Enunciati e temi sono formulati in modo neutro e non etichettati come destra o sinistra.

## Alternative considerate
Profilo lato server con account: scartato per rischio GDPR e di data breach. Profilazione implicita dal comportamento di navigazione: scartata come manipolativa e non trasparente.

## Conseguenze
Nessuna personalizzazione basata su LLM lato server per il livello valoriale, per coerenza con ADR 0008. Più semplice la valutazione d'impatto privacy, meno dati per migliorare il prodotto: il miglioramento avverrà tramite test con utenti volontari.
