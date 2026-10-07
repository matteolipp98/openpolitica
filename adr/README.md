# Architecture Decision Records

Applicazione pubblica che aiuta i cittadini a valutare i principali esponenti politici italiani su due piani distinti: quello fattuale, uguale per tutti, e quello valoriale, relativo al credo etico di ciascun utente.

Formato: Contesto, Decisione, Alternative considerate, Conseguenze. Tutti gli ADR sono in stato **Proposto** finché non vengono approvati.

| ADR | Titolo |
|---|---|
| [0001](0001-separazione-fatti-valori.md) | Separazione tra livello fattuale e livello valoriale |
| [0002](0002-fonti-e-ingestion.md) | Fonti e ingestion near-real-time e storica |
| [0003](0003-copyright-conservazione.md) | Diritto d'autore e politica di conservazione dei contenuti |
| [0004](0004-pipeline-a-stadi.md) | Pipeline agentica a stadi con responsabilità strette |
| [0005](0005-modello-dati-temporale.md) | Modello dati temporale e tracciabilità delle fonti |
| [0006](0006-mitigazione-bias.md) | Strategia misurabile di mitigazione del bias |
| [0007](0007-profilo-valoriale-client-side.md) | Profilo valoriale dell'utente calcolato lato client |
| [0008](0008-algoritmo-affinita.md) | Algoritmo di affinità deterministico e spiegabile |
| [0009](0009-presentazione-no-score-unico.md) | Nessun punteggio unico e UX contro l'effetto bolla |
| [0010](0010-conformita-normativa.md) | Conformità normativa: AI Act, GDPR, DSA, par condicio, diffamazione |
| [0011](0011-stack-aws.md) | ~~Stack tecnologico su AWS~~ (sostituito da 0017) |
| [0012](0012-governance-trasparenza.md) | Governance, trasparenza e diritto di replica |
| [0013](0013-assistente-conversazionale.md) | Assistente conversazionale con raccomandazione motivata |
| [0014](0014-fact-checking-dati-reali.md) | Fact-checking basato su dati reali e calcoli deterministici |
| [0015](0015-generazione-ancorata-fonti.md) | Generazione ancorata alle fonti e validazione delle citazioni |
| [0016](0016-laboratorio-bias-modelli.md) | Laboratorio di misurazione del bias tra modelli e famiglie |
| [0017](0017-stack-vercel-render-supabase-litellm.md) | Stack: Vercel, Render, Supabase e LiteLLM |
| [0018](0018-jev-decisioni-tipizzate.md) | ~~Jev come livello di decisioni tipizzate~~ (sostituito da 0031) |
| [0019](0019-statistiche-aggregate.md) | Statistiche aggregate e regola del denominatore |
| [0020](0020-analisi-programmi-promesse.md) | Analisi dei programmi e realismo delle promesse |
| [0021](0021-modalita-elettorale.md) | Oggetto del voto e modalità elettorale |
| [0022](0022-catalogo-enunciati.md) | Catalogo degli enunciati |
| [0023](0023-profondita-storica.md) | Profondità storica e peso temporale delle evidenze |
| [0024](0024-fasi-di-rilascio.md) | Fasi di rilascio e perimetro dell'MVP |
| [0025](0025-repository-e-sviluppo.md) | Struttura del repository e pratiche di sviluppo |
| [0026](0026-robustezza-contenuti-ostili.md) | Robustezza contro contenuti ostili e sicurezza applicativa |
| [0027](0027-anagrafica-identita.md) | Anagrafica dei soggetti e risoluzione delle identità |
| [0028](0028-revisione-umana.md) | Capacità di revisione umana e regole di pubblicazione |
| [0029](0029-sostenibilita-economica.md) | Sostenibilità economica e limiti di spesa |
| [0030](0030-catalogo-generato-automaticamente.md) | Catalogo generato automaticamente e controlli sostitutivi della revisione umana |
| [0031](0031-laya-al-posto-di-jev.md) | Laya al posto di Jev come motore di decisione |
| [0032](0032-esecuzione-laya.md) | Esecuzione e deployment di Laya |
| [0033](0033-calibrazione-e-astensione.md) | Calibrazione, soglie di confidenza e astensione |
| [0034](0034-adattamento-dominio.md) | Adattamento del modello al dominio politico italiano |
| [0035](0035-progettazione-domande-tipizzate.md) | Progettazione delle domande tipizzate |
| [0036](0036-viste-e-regole-di-presentazione.md) | Viste del prodotto e regole di presentazione |
| [0037](0037-allineamento-ai-mock.md) | Allineamento delle regole ai mock delle viste |
| [0038](0038-gemini-fornitore-iniziale.md) | Gemini come unico fornitore di modelli iniziale |
| [0039](0039-kpi-annunci-promesse-laya.md) | Indicatori su annunci e promesse con Laya |
| [0040](0040-andamento-nel-tempo.md) | Andamento dei partiti nel tempo |

Documenti di accompagnamento: [architettura MVP e flussi logici](architettura-mvp.md) e i mock in `mockup/`, che sono la specifica visiva dell'ADR 0036.

| Vista | File | ADR attuati |
|---|---|---|
| Indice dei soggetti | `mockup/vista-soggetti.html` | 0036, 0037, 0019, 0009, 0001 |
| Questionario e risultato | `mockup/vista-questionario.html` | 0036, 0037, 0008, 0007, 0013, 0021, 0030 |
| Scheda di un soggetto | `mockup/vista-partito.html` | 0036, 0037, 0039, 0014, 0020, 0023, 0019, 0001 |
| Andamento nel tempo (in pausa, tolto dal sito) | `mockup/vista-andamento.html` | 0040, 0039, 0019, 0009, 0001 |
| Come funziona | `mockup/vista-comefunziona.html` | 0036, 0037, 0039, 0040, 0012, 0030, 0007, 0031 |
| Il metodo (domande, dati, correzioni) | `mockup/vista-metodo.html` | 0012, 0022, 0023, 0025, 0030, 0036, 0038 |

## Come leggerli

Attivi: tutti tranne 0011 (sostituito da 0017) e 0018 (sostituito da 0031). In modalità iniziale senza revisori umani valgono le modifiche dell'ADR 0030 su 0022 e 0028, a loro volta aggiornate dall'ADR 0037: dove i mock divergevano dagli ADR, allora sono stati gli ADR ad adeguarsi.

Percorso di lettura consigliato: 0001 per il perché, 0024 per l'ordine di sviluppo, 0008 e 0022 per il cuore del calcolo, 0017 e 0032 per lo stack, 0033 prima di toccare qualsiasi soglia.

## Principi guida

Il sistema non dichiara di essere neutrale: dichiara come misura il proprio bias e pubblica i risultati. Nessun verdetto senza fonte citata e senza confronto deterministico con un dato ufficiale. Nessun LLM decide chi è "migliore" né quale partito è più affine all'utente: lo decide un algoritmo pubblico. Nessun numero viene prodotto da un LLM. I voti espressi valgono più delle dichiarazioni. Ogni output è riproducibile a partire da versioni note di fonti, prompt e modelli. Il progetto è anche un laboratorio pubblico per misurare il bias politico di modelli e famiglie di modelli.
