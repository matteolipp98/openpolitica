# ADR 0023 — Profondità storica e peso temporale delle evidenze

**Stato:** Proposto

## Contesto
Lo storico è ottimo per i comportamenti e povero per le parole. I voti elettronici in Assemblea sono pubblicati dalla XIII legislatura, quindi il comportamento parlamentare è retroattivo da subito; le dichiarazioni sui media no, perché GDELT copre una finestra di circa tre mesi e gli archivi delle testate sono in gran parte inaccessibili. Serve inoltre una regola su quanto pesa un'evidenza vecchia e su come trattare chi ha cambiato partito.

## Decisione
**Backfill differenziato.** Si importa tutto lo storico disponibile di voti, atti e resoconti; i programmi elettorali dal 2018, più quanto recuperabile via archivi web; le dichiarazioni solo dal giorno di accensione del sistema in avanti. L'interfaccia dichiara sempre la finestra di copertura di ciascun tipo di evidenza.

**Peso temporale.** La legislatura corrente è il riferimento per il calcolo delle posizioni. Le evidenze precedenti entrano come contesto storico e non nel punteggio di affinità, salvo assenza di evidenze recenti sull'enunciato: in quel caso si usa l'evidenza più recente disponibile, marcata con la sua data e con confidenza ridotta. Nessuna funzione di decadimento continua: una regola a soglie è spiegabile, una curva no.

**Cambi di posizione e di partito.** Un cambio di posizione non viene appianato in una media: si mostrano entrambe le posizioni con le date. Le posizioni seguono la persona; al partito sono attribuiti i comportamenti dei suoi membri nel periodo in cui ne facevano parte.

**Finestre di confronto.** Le statistiche aggregate (ADR 0019) usano finestre identiche per tutti i soggetti, e l'interfaccia impedisce confronti tra finestre diverse.

**Storicizzazione delle correzioni.** Vale il modello bitemporale (ADR 0005): una rettifica non cancella ciò che era stato pubblicato, crea una nuova versione con la data di registrazione.

## Alternative considerate
Decadimento esponenziale del peso delle evidenze: elegante ma opaco per l'utente e difficile da difendere. Includere tutte le legislature nel punteggio: scartato, premia o punisce per posizioni prese in contesti politici non comparabili.

## Conseguenze
Nei primi mesi il fact-checking delle dichiarazioni avrà volumi bassi, mentre coerenza e promesse sono già utilizzabili: è coerente con l'ordine delle fasi. Il valore dell'archivio cresce nel tempo e diventa un vantaggio difficile da replicare.
