# ADR 0029 — Sostenibilità economica e limiti di spesa

**Stato:** Proposto

## Contesto
Le fonti dati sono gratuite, ma modelli, piattaforme e tempo non lo sono. Un'app pubblica con chat è esposta anche a costi imprevedibili: il traffico non è controllabile e ogni sessione consuma inferenza. L'ADR 0012 vieta finanziamenti da partiti e soggetti schierati, quindi il modello economico va risolto entro quel vincolo.

## Decisione
**Struttura dei costi.** Piattaforme (Vercel, Render, Supabase) a costo fisso contenuto. Screening e decisioni tipizzate a costo di solo calcolo, su infrastruttura propria, quindi fisso e non proporzionale al volume (ADR 0031, 0032). Estrazione dei claim, che scala con il volume di documenti. Chat, che scala con gli utenti ed è la voce più volatile. Laboratorio, che scala con la dimensione delle matrici.

**Tetti di spesa obbligatori.** Budget giornalieri e mensili per stadio configurati sul gateway LiteLLM, più un tetto globale. Al superamento il sistema degrada in modo prevedibile e dichiarato: prima si sospende il laboratorio, poi l'ingestion non prioritaria, poi la chat, che passa al questionario strutturato. Il nucleo deterministico (questionario, affinità, pagine pubbliche) non dipende da modelli e resta sempre disponibile (ADR 0021).

**Contenimento strutturale.** Il filtro di perimetro prima di ogni chiamata generativa; caching delle spiegazioni per profili simili; Batch API dei fornitori per il laboratorio; pagine pubbliche statiche con rigenerazione incrementale, così il traffico di lettura non genera costo di inferenza.

**Osservabilità del costo.** Ogni run registra costo e modello (ADR 0016), con un cruscotto per stadio. Il costo per documento e per sessione di chat sono metriche di prodotto monitorate.

**Finanziamento.** Donazioni individuali, fondi per progetti civici o di ricerca, contributi di fondazioni indipendenti. Sono esclusi finanziamenti da partiti, candidati, comitati elettorali e soggetti politicamente schierati; le fonti di finanziamento sono pubblicate (ADR 0012). Nessuna pubblicità, nessuna vendita di dati, nessuna versione a pagamento delle funzioni di voto: la differenziazione a pagamento su uno strumento elettorale sarebbe di per sé un problema di equità.

## Alternative considerate
Chat aperta senza tetti: scartata, un picco di traffico o un abuso possono generare spese arbitrarie. Modello freemium: scartato per equità. Sponsorizzazioni da media: da valutare caso per caso, con gli stessi criteri di indipendenza.

## Conseguenze
Serve un tetto deciso prima del lancio e accettare che al suo superamento il servizio si degradi invece di indebitarsi. Il degrado va progettato e testato, non improvvisato: è parte dei requisiti dell'MVP.
