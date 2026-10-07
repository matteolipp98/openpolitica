# ADR 0018 — Jev come livello di decisioni tipizzate

**Stato:** Sostituito da ADR 0031 (Laya, pesi aperti e self-hosting)
**Estende:** ADR 0004, 0015, 0016

## Contesto
Gran parte della pipeline non deve generare testo: deve decidere. Screening, classificazione, posizionamento su una scala e verifica di supporto tra evidenza e frase sono decisioni tipizzate. Farle con un LLM generativo significa pagare token di output, accettare output non vincolati e perdere la probabilità associata alla decisione.

Jev (TypeSafe AI) è un modello che risponde a domande tipizzate su uno stato con tre primitivi: Choice, che sceglie un'opzione restituendo le probabilità di tutte, Score, che valuta su livelli ordinati, e Noul, che restituisce la probabilità che un'affermazione sia vera. Costa 0,042 dollari per milione di token in input con output gratuito, risponde in poche centinaia di millisecondi ed è già integrato in LiteLLM, quindi entra nello stack senza modifiche architetturali.

## Decisione
Jev diventa il livello di decisione della pipeline, nei punti seguenti.

**Filtro di perimetro (stadio 0).** Noul su "il documento riporta una dichiarazione di un politico monitorato". Sostituisce il NER e taglia il volume prima di qualunque chiamata generativa.

**Classificazione (stadio 3).** Choice per tipo di claim e per tema, dalla tassonomia versionata.

**Posizionamento (stadio 6).** Score sulla scala da contrario a favorevole rispetto agli enunciati. Le probabilità per livello alimentano direttamente la confidenza della posizione (ADR 0008): sotto una soglia non si registra alcuna posizione.

**Validazione delle citazioni (ADR 0015).** Noul su "questa evidenza supporta la frase".

**Guardrail della chat (ADR 0013).** Noul su "la richiesta è fuori perimetro".

Restano ai modelli generativi tre compiti: estrarre i claim dal testo, condurre la conversazione, scrivere le spiegazioni.

**Contromisure.** Jev è un modello chiuso di un singolo fornitore: se decide da solo classificazione e posizioni diventa un punto unico di bias, contro il principio dell'ensemble. Quindi un campione stratificato di ogni stadio viene rieseguito con modelli OpenAI e Anthropic e il disaccordo è monitorato; Jev è un soggetto misurato nel laboratorio (ADR 0016) come gli altri; la calibrazione delle probabilità viene verificata contro il golden set umano e, se serve, ricalibrata con una funzione appresa sui dati etichettati, versionata come il resto. Le posizioni pubblicate restano soggette a revisione umana.

**Versioni e accesso.** Si usa sempre un identificativo di modello con versione fissata, mai un alias mobile, perché le valutazioni devono restare confrontabili nel tempo. L'accesso diretto è su lista d'attesa; gateway come OpenRouter o Vercel AI Gateway lo espongono senza attesa. Il fallback, se il servizio è indisponibile o l'accesso viene meno, è una classificazione equivalente con un LLM generativo a output strutturato: più lenta e più costosa, ma senza cambiare lo schema dati.

## Alternative considerate
Modelli generativi con output strutturato per tutti gli stadi: più costosi, più lenti, senza probabilità calibrate. Classificatori addestrati in casa: richiedono dati etichettati che oggi non esistono; restano un'opzione quando il golden set sarà ampio.

## Conseguenze
Costo per documento molto basso, quindi il perimetro può essere allargato senza esplosione di spesa. Le decisioni diventano numeriche e questo rende il test controfattuale (ADR 0006) una misura continua invece di un conteggio di ribaltamenti. Si aggiunge un fornitore al registro dei trattamenti: la chat invia allo stesso fornitore le risposte dell'utente, quindi valgono i vincoli di ritenzione dell'ADR 0013.
