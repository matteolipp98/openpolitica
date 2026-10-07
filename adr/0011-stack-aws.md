# ADR 0011 — Stack tecnologico su AWS

**Stato:** Sostituito da ADR 0017

## Contesto
La pipeline combina ingestion continua, elaborazione LLM a stadi, retrieval su fonti e un frontend pubblico con calcolo lato client. Serve uno stack gestito, osservabile, con residenza dei dati in UE e accesso a più famiglie di modelli (ADR 0006).

## Decisione
**Ingestion:** EventBridge Scheduler e Lambda o container Fargate per il polling di feed, GDELT e siti ufficiali; job batch per il backfill storico; S3 come zona grezza temporanea con lifecycle coerente con ADR 0003. Transcribe o un modello Whisper self-hosted per audio e video.

**Orchestrazione:** SQS per il disaccoppiamento tra ingestion ed elaborazione; Step Functions per il flusso deterministico degli stadi per ogni documento; code separate con priorità per il flusso real-time e il backfill.

**Agenti e modelli:** Bedrock per l'accesso a più famiglie di modelli; AgentCore per runtime, identità, memoria e osservabilità degli agenti degli stadi di estrazione, verifica e steelman. Prompt e configurazioni versionati nel repository.

**Storage e retrieval:** OpenSearch con ricerca ibrida lessicale e vettoriale per claim, documenti istituzionali e retrieval della verifica; Neptune per il grafo delle relazioni (ADR 0005); Aurora PostgreSQL per anagrafiche e dati transazionali; S3 con Iceberg e Athena per analisi e suite di valutazione.

**Assistente conversazionale:** AgentCore Runtime per intervistatore e spiegatore con sessioni effimere; API Gateway WebSocket per lo streaming; Bedrock Guardrails per filtri di contenuto e rifiuto degli argomenti fuori perimetro; memoria di sessione solo in RAM, senza memoria persistente.

**Dati ufficiali e calcolo:** servizio dedicato di connettori verso ISTAT SDMX, Eurostat e le altre fonti dell'ADR 0014, con cache versionata delle serie su S3 e motore di confronto deterministico in Python eseguito su Lambda o Fargate.

**Revisione umana:** interfaccia interna dedicata o SageMaker Ground Truth per golden set e revisione.

**Frontend:** applicazione web statica su CloudFront e S3 con calcolo delle affinità in browser (ADR 0007, 0008); API pubbliche in sola lettura tramite API Gateway con caching aggressivo.

Tutto in regione UE, infrastruttura come codice.

## Alternative considerate
Framework agentico open source su Kubernetes: valido, ma aumenta il carico operativo. Unico provider di modelli via API diretta: scartato per il requisito di ensemble.

## Conseguenze
Dipendenza da AWS mitigata da interfacce astratte verso modelli e storage. Neptune va rivalutato dopo il prototipo: se le query di grafo sono poche può essere sostituito da tabelle di relazione in PostgreSQL.
