# ADR 0001 — Separazione tra livello fattuale e livello valoriale

**Stato:** Proposto

## Contesto
L'obiettivo è duplice: permettere un giudizio oggettivo e, allo stesso tempo, un giudizio coerente con l'etica dell'utente. Questi due obiettivi entrano in conflitto se vengono fusi: un sistema che incorpora un'etica "di default" smette di essere oggettivo, e un sistema che pretende di essere solo oggettivo nasconde scelte valoriali dentro criteri apparentemente tecnici (per esempio quali temi contano).

## Decisione
L'applicazione è organizzata in due livelli rigidamente separati.

Il **livello fattuale** è identico per tutti gli utenti e risponde a domande verificabili: cosa ha detto, quando, cosa ha votato, se un dato citato corrisponde alle fonti ufficiali, se una promessa è stata seguita da atti, se dichiarazioni e voti sono coerenti nel tempo.

Il **livello valoriale** non contiene alcun giudizio prodotto dal sistema. Confronta le posizioni documentate del politico con le posizioni dichiarate dall'utente e mostra concordanze e discordanze. L'etica è dell'utente, il sistema fornisce solo lo specchio.

I dati del livello valoriale derivano esclusivamente dal livello fattuale, mai il contrario.

## Alternative considerate
Un punteggio etico calcolato dal sistema: scartato perché impone una morale e rende il progetto politicamente schierato per costruzione. Solo livello fattuale: scartato perché non risponde al bisogno reale dell'utente, che vota in base ai valori.

## Conseguenze
Due superfici UX distinte e due set di metriche di qualità. Il livello fattuale richiede verifica rigorosa; il livello valoriale richiede soprattutto trasparenza e controllo dei dati personali (vedi ADR 0007). Diventa possibile difendere pubblicamente il progetto: i fatti sono tracciabili, i valori sono dell'utente.
