# ADR 0010 — Conformità normativa

**Stato:** Proposto, modificato da ADR 0037 (esiti quantitativi pubblicati senza revisione umana)

## Contesto
Un'applicazione pubblica basata sull'AI che aiuta i cittadini a valutare i politici tocca più ambiti normativi. Questo ADR fissa l'approccio; ogni punto richiede verifica con un legale prima del lancio.

## Decisione
**AI Act.** Tra i sistemi ad alto rischio l'AI Act elenca quelli destinati a influenzare l'esito di elezioni o il comportamento di voto delle persone. È plausibile che l'app rientri in questa categoria. Si progetta fin dall'inizio come se lo fosse: gestione del rischio, governance dei dati, documentazione tecnica, logging, supervisione umana, accuratezza e trasparenza verso l'utente. Le tempistiche di applicazione degli obblighi vanno verificate al momento del lancio. Gli obblighi di trasparenza sui contenuti generati dall'AI si applicano comunque.

**GDPR.** Il profilo valoriale è gestito come descritto in ADR 0007. I dati sui politici riguardano l'attività pubblica e vanno limitati a questa, escludendo la vita privata. Valutazione d'impatto sulla protezione dei dati prima del lancio.

**Diffamazione.** Nessun esito "contraddetto" senza fonte citata. Per i claim quantitativi l'esito si pubblica senza revisione umana alle condizioni dell'ADR 0037 (citazione verificata, accordo tra famiglie di modelli, confronto deterministico con tolleranza pubblicata); "fuorviante per contesto" richiede revisione umana. Il parere legale deve esaminare esplicitamente questa scelta. Linguaggio descrittivo e non valutativo ("il dato citato differisce da quello ISTAT"), mai attributivo di intenzioni ("ha mentito").

**Par condicio e periodi elettorali.** Durante le campagne elettorali vanno verificati gli obblighi applicabili ai servizi online e le indicazioni AGCOM. Si prevede una modalità elettorale con regole di parità di trattamento rafforzate e congelamento dei cambi metodologici.

**DSA.** Se l'app ospita contenuti degli utenti (commenti, segnalazioni) si applicano gli obblighi di moderazione e segnalazione.

**Diritto d'autore.** Vedi ADR 0003.

**Assistente e raccomandazione (ADR 0013).** La presenza di un chatbot che indica i partiti più affini rafforza la probabile classificazione ad alto rischio. L'utente viene informato che interagisce con un sistema AI, che il risultato deriva da un algoritmo pubblico e che non è un'indicazione di voto. La conversazione contiene opinioni politiche: consenso esplicito, nessuna conservazione, alternativa senza chatbot.

**Policy dei fornitori di modelli.** Le condizioni d'uso di alcuni fornitori limitano applicazioni legate a elezioni e campagne politiche. Prima di scegliere i modelli dell'ensemble va verificato che questo caso d'uso sia ammesso da ciascuno, eventualmente con richiesta di autorizzazione specifica.

## Alternative considerate
Rimandare la conformità alla fase di crescita: scartato perché l'architettura (logging, versioning, revisione umana, privacy lato client) è molto più costosa da introdurre dopo.

## Conseguenze
Documentazione tecnica mantenuta come parte del codice, logging completo della pipeline, registro dei rischi. Parere legale e valutazione d'impatto sono prerequisiti del lancio.
