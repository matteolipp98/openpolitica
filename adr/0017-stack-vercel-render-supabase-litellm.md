# ADR 0017 — Stack: Vercel, Render, Supabase e LiteLLM

**Stato:** Proposto, modificato da ADR 0038 (Gemini chiamato direttamente dal job di catalogo)
**Sostituisce:** ADR 0011

## Contesto
Il progetto non verrà distribuito direttamente su un hyperscaler. Il deploy avviene su piattaforme gestite (Vercel, Render, Supabase) e i modelli sono chiamati tramite API dirette di OpenAI e Anthropic, con LiteLLM come strato di astrazione. Lo stack deve comunque supportare ingestion continua, pipeline a stadi affidabile, retrieval ibrido, assistente in streaming e laboratorio multi-modello (ADR 0016).

## Decisione
**Frontend e API pubbliche su Vercel.** Applicazione Next.js: profili dei politici, schede di fact-checking, questionario e calcolo delle affinità nel browser (ADR 0007, 0008). Le route dell'assistente conversazionale sono funzioni server in streaming che chiamano il gateway LiteLLM. Pagine pubbliche generate staticamente e rigenerate incrementalmente. Funzioni configurate in regione europea.

**Gateway LiteLLM su Render.** LiteLLM Proxy come servizio Docker unico punto di uscita verso i modelli: chiavi dei fornitori centralizzate, alias di modello mappati a versioni fissate, fallback, limiti di budget per stadio ed esperimento con degrado controllato al superamento (ADR 0029), metadati di tracciamento su ogni chiamata. Due tipi di route: la route della chat con logging dei contenuti disattivato (ADR 0013), le route di pipeline e laboratorio con logging completo verso il database.

**Motore di decisione su Render.** Servizio Docker dedicato che espone Laya via HTTP ai worker e alle route della chat (ADR 0031, 0032), con checkpoint precaricato e versione fissata. Non passa dal gateway LiteLLM, che resta il punto di uscita verso i soli fornitori esterni.

**Worker e schedulazione su Render.** Cron job per il polling di feed RSS, GDELT e siti ufficiali. Background worker Python per gli stadi della pipeline, i connettori dei dati ufficiali (ISTAT SDMX, Eurostat, UPB, RGS) e il motore di confronto deterministico (ADR 0014). Job separati per backfill storico ed esperimenti del laboratorio, così da non rallentare il flusso real-time.

**Orchestrazione su Postgres.** In assenza di un servizio di workflow gestito, gli stadi comunicano tramite code Postgres (Supabase Queues, basate su pgmq) con una tabella di stato per documento e per claim: ogni stadio è idempotente, i messaggi falliti vanno in una coda di scarto con tentativi limitati. Se la complessità cresce si valuterà un motore di workflow durevole dedicato.

**Dati su Supabase.** Postgres come unico database: anagrafiche, modello bitemporale (ADR 0005), relazioni del grafo come tabelle di archi interrogate con CTE ricorsive, retrieval ibrido con pgvector e ricerca full-text con configurazione italiana. Registro dei modelli, run e risultati del laboratorio nello stesso database, con esportazione periodica in Parquet su Supabase Storage per analisi pesanti con DuckDB. Supabase Storage anche per i documenti grezzi temporanei, con job di cancellazione coerente con l'ADR 0003. Progetto in regione UE.

**Autenticazione.** I cittadini usano l'app in forma anonima. Supabase Auth solo per revisori, panel e amministratori, con Row Level Security per ruolo. L'interfaccia di revisione umana e annotazione del golden set è un'app Next.js interna.

**Moderazione e guardrail.** Senza servizi gestiti di guardrail: endpoint di moderazione del fornitore, hook di guardrail di LiteLLM, un classificatore di perimetro prima della risposta e la validazione dell'ADR 0015 dopo.

**Osservabilità.** Tracce di pipeline e laboratorio tramite callback di LiteLLM verso uno strumento di tracing per LLM (per esempio Langfuse, anche self-hosted su Render), escluse le conversazioni degli utenti.

## Alternative considerate
Hyperscaler con servizi gestiti (ADR 0011): scartato per scelta di progetto. Chiamate dirette agli SDK dei fornitori senza LiteLLM: scartato perché il laboratorio multi-modello richiede un'interfaccia uniforme. Database separati per vettori e grafo: rimandato, Postgres è sufficiente per i volumi attesi.

## Conseguenze
Stack più semplice ed economico da gestire per un team piccolo, con meno garanzie operative sull'orchestrazione, che va costruita e testata con cura.

**Privacy e trasferimenti.** Vercel, Render e Supabase sono sub-responsabili del trattamento, e a loro volta si appoggiano a infrastrutture cloud: vanno censiti nel registro dei trattamenti con i relativi accordi. OpenAI e Anthropic elaborano i dati sulle proprie infrastrutture: per le conversazioni dell'assistente, che contengono opinioni politiche, prima del lancio va verificata la disponibilità di zero data retention, delle opzioni di residenza dei dati in UE e delle garanzie per il trasferimento extra UE.

**Limiti di piattaforma.** Timeout delle funzioni Vercel per lo streaming, dimensionamento dei worker Render per le matrici del laboratorio e limiti di connessioni di Supabase vanno verificati con un prototipo di carico.
