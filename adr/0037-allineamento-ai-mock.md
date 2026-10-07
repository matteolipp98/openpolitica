# ADR 0037 — Allineamento delle regole ai mock delle viste

**Stato:** Proposto
**Modifica:** ADR 0007, 0008, 0009, 0010, 0013, 0019, 0020, 0028, 0030, 0036

## Contesto
I mock in `mockup/` sono stati rivisti dopo gli ADR e sono la versione più aggiornata del prodotto. In alcuni punti mostrano cose che gli ADR vietano o non prevedono:

- la pagina "Come funziona" chiude l'esempio con un esito esplicito, "Numero sbagliato";
- l'indice dei soggetti apre con letture comparative ("è quello che sbaglia più numeri", "è il più vago") e descrive ciascun soggetto con una frase qualitativa ("sbaglia spesso i numeri");
- le schede mostrano conteggi di numeri sbagliati, di voti contrari a quanto dichiarato e di promesse mantenute, e lo stato di ogni promessa;
- il questionario ha tre risposte, una casella "conta più degli altri" per domanda, un pareggio con margine fisso e una scomposizione per domanda, senza intervallo di incertezza né pesi per tema.

L'ADR 0030 fermava la pubblicazione di ogni esito finché non ci fosse stata revisione umana. I mock scelgono invece un prodotto che dice chiaramente quando un numero non torna, in linguaggio comune. Questo ADR porta le regole al livello dei mock e fissa le condizioni che rendono quella scelta difendibile senza revisori.

## Decisione

### Esiti pubblicati per i claim quantitativi
Per i claim quantitativi l'esito si pubblica senza revisione umana, perché lo produce un confronto deterministico con una serie ufficiale e una tolleranza pubblicata (ADR 0014), non un giudizio. Esiti pubblici, in linguaggio comune:

| Esito interno | In pagina |
|---|---|
| supportato | "Il numero è giusto" |
| impreciso | "Quasi giusto", con il numero vero |
| contraddetto | "Numero sbagliato", con un confronto concreto ("il numero vero è meno della metà") |
| non verificabile | "Non si può controllare", con il motivo |

Un esito negativo si pubblica solo se valgono tutte queste condizioni:

1. la citazione è letterale e compare in una fonte di livello A o B, oppure in almeno due fonti di livello C indipendenti (ADR 0002);
2. l'interrogazione strutturata (metrica, periodo, territorio, unità) estratta dal claim coincide per due famiglie di modelli diverse; se non coincide l'esito è "non verificabile" (ADR 0006);
3. se la metrica ammette più definizioni ufficiali, il valore dichiarato è fuori tolleranza rispetto a **tutte**;
4. accanto all'esito compaiono sempre il valore ufficiale, la serie, il periodo e il link.

"Fuorviante per contesto" resta soggetto a revisione umana e non si pubblica senza (ADR 0014, 0028).

Il linguaggio resta descrittivo: si dice che il numero è sbagliato, mai che la persona ha mentito o ha voluto ingannare (ADR 0010).

### Claim fattuali non numerici
Le affermazioni non numeriche verificabili su un testo normativo o un atto ufficiale (per esempio "abbiamo abbassato le tasse a tutte le famiglie" confrontata con la legge di bilancio) si pubblicano come accostamento "Ha detto / In realtà", con l'atto citato, solo quando due famiglie di modelli concordano sull'esito e la fonte è di livello A. Non entrano nel conteggio "numeri sbagliati".

### Letture comparative e frasi qualitative
L'indice dei soggetti può aprire con letture del tipo "X è quello che sbaglia più numeri", a queste condizioni:

- ogni lettura riguarda **una sola metrica** dell'ADR 0019, mai una combinazione;
- il confronto è solo tra soggetti con denominatore pari almeno alla soglia minima, nella stessa finestra temporale e sulle stesse fonti;
- se più soggetti sono a pari valore, si nominano tutti;
- la frase porta sempre con sé numeratore e denominatore;
- le regole che generano le letture e le frasi qualitative ("sbaglia spesso", "di solito è giusto", "così così") sono dati versionati e pubblici, con le soglie esplicite (ADR 0025); oggi: almeno 15% "spesso", al massimo 6% "di solito è giusto", sotto 30 controlli nessun giudizio ma "ha detto pochi numeri controllabili".

Resta vietato un indice sintetico di affidabilità (ADR 0009, 0019): le letture sono frasi distinte, una per metrica, e l'elenco dei soggetti resta in ordine alfabetico.

### Statistiche aggregate
Le metriche dell'ADR 0019 si pubblicano da subito, con la regola del denominatore, la soglia minima e il conteggio sempre visibile. Il conteggio accompagna ogni percentuale anche quando il mock non lo mostra in grande: per il tasso di frasi non controllabili va nella riga sotto la cifra.

### Stato delle promesse
Lo stato "Mantenuta / A metà / Non mantenuta" si pubblica senza revisione quando deriva da regole fisse su atti istituzionali:

- **mantenuta:** esiste un atto approvato e in vigore che realizza la misura, oppure il dato ufficiale raggiunge l'obiettivo quantificato;
- **a metà:** l'atto è temporaneo o parziale, oppure il dato ufficiale si muove nella direzione promessa senza raggiungere l'obiettivo;
- **non mantenuta:** nessun atto presentato nel periodo, oppure il soggetto ha votato contro l'atto che la realizzava.

Il collegamento tra promessa e atti richiede l'accordo di due famiglie di modelli; senza accordo la promessa resta "da verificare" e non entra nei conteggi. Ogni stato mostra la frase di motivazione e l'atto o la serie da cui deriva. Resta la normalizzazione per ruolo dell'ADR 0019: accanto ai conteggi si dichiara se il soggetto era al governo o all'opposizione.

### Questionario
Il questionario segue il mock:

- tre risposte: "Sono d'accordo" (+2), "Sono contrario" (−2), "Non ho un'opinione" (domanda esclusa dal calcolo);
- una casella per domanda, "Questo argomento per me conta più degli altri", che raddoppia il peso della domanda; sostituisce i pesi per tema dell'ADR 0007;
- per ogni domanda, una scheda "Prima di rispondere" con il contesto fattuale e gli argomenti di chi è a favore e di chi è contro, in forma simmetrica (ADR 0013, 0014);
- punteggio per domanda `4 − |utente − soggetto|`, moltiplicato per il peso; affinità uguale alla somma dei punti diviso il massimo possibile;
- se il soggetto non ha posizione documentata la domanda non entra nel calcolo e si dice su quante domande manca il dato;
- se la posizione del soggetto è neutra (0) la domanda non conta né come accordo né come disaccordo;
- se non resta nessuna domanda confrontabile non si mostra una percentuale;
- pareggio: sono alla pari tutti i soggetti entro 3 punti dal primo; sostituisce l'intervallo di incertezza dell'ADR 0013;
- "nessuno ti rappresenta" sotto il 50% di affinità del primo (ADR 0021);
- il risultato si scompone per domanda, con accordi, disaccordi e dati mancanti; sostituisce la scomposizione per tema dell'ADR 0009;
- per vedere come cambia il risultato l'utente torna indietro o rifà le domande; non c'è un pannello dei pesi.

Margine di pareggio, soglia "nessuno ti rappresenta" e peso della casella sono parametri versionati.

## Alternative considerate
**Mantenere l'ADR 0030 e cambiare i mock:** scartata, i mock rappresentano la scelta di prodotto più recente, e un sito che non dice mai se un numero è sbagliato non risponde alla domanda dell'elettore. **Pubblicare anche gli esiti "fuorviante per contesto":** scartata, la regola che li produce contiene una scelta di finestra temporale che senza revisione è attaccabile. **Pesi per tema oltre alla casella per domanda:** rimandata, aggiunge complessità che il mock ha tolto.

## Conseguenze
Il rischio diffamatorio aumenta e si sposta dalla revisione umana alla qualità delle regole: tolleranze, catalogo indicatori, accordo tra famiglie e condizioni sulle fonti diventano la vera difesa e vanno pubblicati. Il parere legale dell'ADR 0010 deve esaminare esplicitamente questa scelta prima del lancio pubblico. Il canale di replica e la pagina delle correzioni (ADR 0012) diventano il presidio principale dopo la pubblicazione: una segnalazione su un esito negativo lo sospende fino alla verifica.

Le letture comparative rendono le asimmetrie tra schieramenti molto visibili: l'audit di copertura dell'ADR 0006 va pubblicato insieme, raggiungibile dalla stessa pagina.

Quando esiste capacità di revisione si aggiungono il campionamento a posteriori e la doppia revisione dell'ADR 0028 sugli esiti negativi, senza cambiare cosa si pubblica.
