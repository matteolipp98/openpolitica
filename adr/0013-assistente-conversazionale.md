# ADR 0013 — Assistente conversazionale con raccomandazione motivata

**Stato:** Proposto
**Modifica:** ADR 0007, 0008, 0009

## Contesto
Un questionario statico è poco coinvolgente e non permette di approfondire i trade-off. Si vuole un assistente che faccia domande in modo proattivo, adatti l'intervista alle risposte e alla fine indichi i partiti e i politici più vicini all'utente, motivando con dati e fonti.

È la componente a rischio più alto del progetto. Un LLM che conversa di politica e poi indica un partito può orientare il voto con il framing delle domande, con l'ordine dei temi, con il tono della spiegazione o con un'allucinazione. Deve quindi essere persuasivo nel metodo e mai nel merito.

## Decisione
L'assistente ha tre ruoli separati, e solo il primo e il terzo usano un LLM.

**1. Intervistatore.** Conduce la conversazione scegliendo le domande da un catalogo di enunciati approvati dal panel (ADR 0012). Può riformularle in linguaggio naturale, ma non inventa domande nuove né cambia il loro framing. La selezione della domanda successiva segue una regola pubblica: prima una copertura minima obbligatoria di tutti i temi, in ordine casuale, poi approfondimenti sui temi in cui le risposte dell'utente discriminano meglio tra i politici.

Prima di chiedere una posizione su una misura, l'intervistatore mostra i dati di contesto rilevanti in forma simmetrica: cosa costa secondo le stime ufficiali, quali effetti sono documentati, quali argomenti portano i favorevoli e i contrari (ADR 0014). È qui che entra il dato reale che nel dibattito politico manca.

Dopo ogni risposta l'LLM estrae una posizione strutturata (scala da contrario a favorevole, più importanza del tema) e la **mostra all'utente per conferma**. Il profilo è sempre visibile e modificabile, e fa fede solo il profilo confermato, non la trascrizione.

**2. Motore di affinità.** Il profilo confermato alimenta l'algoritmo deterministico dell'ADR 0008, eseguito sul client. Nessun LLM decide il risultato.

**3. Spiegatore.** Riceve un pacchetto di evidenze chiuso: punteggi scomposti per tema, voti, dichiarazioni, esiti di fact-checking e promesse, ciascuno con identificativo di fonte. Genera la motivazione solo da quel pacchetto, con i vincoli dell'ADR 0015.

**Forma della raccomandazione.** L'output è una graduatoria completa per affinità, con il primo in evidenza e l'intervallo di incertezza. Se più partiti o politici sono entro il margine di incertezza vengono presentati come pari. Per ciascuno si mostrano le concordanze principali, le **discordanze principali**, il track record fattuale e lo stato delle promesse sui temi importanti per l'utente. Il linguaggio è "più vicino alle tue risposte", mai "dovresti votare". L'utente vede sempre come cambierebbe il risultato modificando i pesi dei temi.

**Comportamento dell'assistente.** Non esprime opinioni proprie, non commenta la moralità delle risposte dell'utente, rifiuta richieste di attacchi, propaganda o contenuti fuori catalogo. Se l'utente chiede "chi devo votare?" senza aver completato l'intervista, spiega il metodo e propone di iniziarla.

## Alternative considerate
LLM che raccomanda direttamente in base alla conversazione: scartato perché non riproducibile, non auditabile e manipolabile con il prompt. Nessuna raccomandazione, solo profili: scartato perché non risponde al bisogno dell'utente. Un solo vincitore senza graduatoria: scartato perché nasconde l'incertezza e le distanze reali.

## Conseguenze
La conversazione transita necessariamente dal server per l'inferenza, e questo modifica l'ADR 0007 (vedi sotto). Serve una suite di test a utenti sintetici: persone simulate con profili noti attraversano l'intervista, e si verifica che la graduatoria finale coincida con quella calcolata compilando direttamente il questionario strutturato. Divergenze sistematiche per orientamento dell'utente simulato indicano che la conversazione orienta, e bloccano il rilascio. Si testano anche ordine delle domande, tono e lunghezza delle spiegazioni per schieramento.

### Modifiche ad altri ADR
**0007.** Il profilo confermato resta sul client. La conversazione viene elaborata dal server in modo effimero: nessuna persistenza della trascrizione, log solo di metadati tecnici privi di contenuto, consenso esplicito ai sensi dell'art. 9(2)(a) GDPR prima di iniziare, decisioni tipizzate eseguite sull'infrastruttura del progetto senza uscire verso terzi (ADR 0031), fornitori di modelli generativi configurati con zero data retention e senza uso per addestramento, con opzioni di residenza dei dati in UE dove disponibili (ADR 0017). Resta sempre disponibile il questionario strutturato senza chatbot per chi non vuole inviare le proprie opinioni a un server.

**0008.** Il calcolo dell'affinità resta deterministico e privo di LLM. Gli LLM a runtime sono ammessi solo nei ruoli di intervistatore e spiegatore.

**0009.** La graduatoria per affinità è consentita come esito dell'assistente, con incertezza, pareggi e discordanze sempre visibili. Resta vietato qualsiasi punteggio etico o di "qualità" del politico.
