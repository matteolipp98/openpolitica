# ADR 0002 — Fonti e ingestion near-real-time e storica

**Stato:** Proposto (rivisto: solo fonti gratuite e solo contenuti testuali)

## Contesto
Servono due flussi: le notizie e dichiarazioni recenti, per capire cosa viene annunciato, e lo storico, per valutare coerenza e mantenimento delle promesse. La scelta delle fonti è il primo punto di ingresso del bias: se il corpus sovrarappresenta certe testate o certi politici, ogni stadio successivo eredita la distorsione.

Vincoli di progetto: nessuna API a pagamento, e solo contenuti testuali. Si usano open data, feed pubblici e API gratuite, nel rispetto dei rispettivi termini d'uso. Audio e video non vengono acquisiti né trascritti.

## Decisione

### Livelli di affidabilità
Ogni documento porta con sé il livello della fonte da cui proviene.

**Livello A, fonti primarie istituzionali.** Si tratta di Camera e Senato, Gazzetta Ufficiale e Normattiva, programmi elettorali depositati, comunicati ufficiali di governo, ministeri e partiti.

**Livello B, fonti primarie non istituzionali.** Rientrano qui i testi pubblicati direttamente dai politici su canali ufficiali, come i canali Telegram.

**Livello C, fonti giornalistiche.** Servono solo per scoprire che una dichiarazione è avvenuta. Il claim viene poi ancorato, quando possibile, alla fonte primaria.

### Flusso near-real-time
Il flusso gira come cron job su Render, con intervalli da 5 a 15 minuti a seconda della fonte.

**Feed RSS.** Il paniere comprende agenzie di stampa, Palazzo Chigi, ministeri e un insieme di testate bilanciato per orientamento editoriale. La composizione del paniere è resa pubblica. Si scaricano solo i contenuti nuovi, verificati tramite ETag, Last-Modified e hash del contenuto.

**GDELT DOC API.** È gratuita e si aggiorna ogni 15 minuti. Si interroga per nome dei politici del perimetro, così da coprire articoli che non compaiono nel paniere RSS.

**Siti ufficiali di partiti e politici.** Sulle pagine news si fa scraping leggero con estrazione del testo tramite trafilatura, rispettando robots.txt e con rate limit per dominio.

**Telegram.** Dai canali pubblici dei politici e dei partiti si acquisisce solo il testo dei messaggi, tramite MTProto con Telethon. Allegati audio, video e immagini vengono ignorati.

**Camera e Senato.** Resoconti stenografici, ordini del giorno e votazioni vengono acquisiti con cadenza giornaliera.

### Flusso storico
È un backfill batch eseguito come job separato, per non rallentare il flusso real-time.

**dati.camera.it e dati.senato.it.** Da endpoint SPARQL e dump si prendono interventi, atti presentati e votazioni nominali delle legislature disponibili.

**Openpolis.** Fornisce anagrafiche, incarichi e attività parlamentare, nei limiti delle condizioni d'uso gratuite da verificare.

**Programmi elettorali.** Dal 2018 si prendono dal portale del Ministero dell'Interno. Per i programmi precedenti o non più online si usano gli snapshot recuperati tramite la CDX API della Wayback Machine.

**Gazzetta Ufficiale e Normattiva.** Servono per collegare promesse e leggi approvate.

**Dati ufficiali per il fact-checking (ADR 0014).** Le fonti sono ISTAT tramite SDMX, Eurostat, Banca d'Italia e OpenBDAP. I documenti di UPB e Corte dei conti vengono scaricati e indicizzati.

### Fonti escluse
**X e Meta (Facebook, Instagram).** Non offrono un accesso gratuito utilizzabile in lettura. Lo scraping è escluso perché viola i termini d'uso ed è fragile. Le dichiarazioni pubblicate su queste piattaforme vengono intercettate indirettamente tramite agenzie, RSS e GDELT; quando possibile si registra l'URL del post originale come riferimento, senza acquisirne il contenuto.

**Audio e video.** Interviste televisive, talk show, dirette e podcast non vengono acquisiti. Per l'attività parlamentare i resoconti stenografici ufficiali coprono già il testo degli interventi. Le dichiarazioni rese in TV o radio entrano nel sistema solo quando vengono riportate per iscritto da agenzie o testate. In quel caso il claim è marcato come riportato da terzi e non come citazione diretta verificata.

**Qualunque API a pagamento** per notizie, social o monitoraggio media.

### Meccanica comune
Ogni fonte è un connettore con la stessa interfaccia, composta da quattro passi: scoperta, download, estrazione del testo, normalizzazione. Il documento normalizzato entra nella coda pgmq (ADR 0017) insieme a fonte, livello, data di pubblicazione, URL e hash.

La **deduplicazione** avviene in due passaggi. Prima si individuano i quasi-duplicati con MinHash, per gli stessi lanci d'agenzia ripresi da più testate. Poi si fa clustering semantico, così la stessa dichiarazione diventa un unico evento con più fonti collegate.

Un **filtro di perimetro** senza LLM precede la pipeline agentica. Un NER leggero con dizionario dei politici e dei loro alias fa entrare negli stadi successivi solo i documenti che nominano un politico monitorato.

Il **perimetro dei politici** segue un criterio oggettivo e pubblico, per esempio leader di partiti sopra una soglia di rappresentanza parlamentare, membri del governo e presidenti di regione, e non una selezione editoriale.

## Alternative considerate
**API commerciali di news e social monitoring.** Sono state scartate per il vincolo sui costi e perché introducono una selezione delle fonti non ispezionabile.

**Scraping dei social senza API.** È stato scartato per i termini d'uso e la fragilità.

**Solo fonti istituzionali.** Sono state scartate come unica fonte perché perdono le dichiarazioni fuori dall'aula, dove avviene gran parte della comunicazione politica.

**Trascrizione di audio e video.** È stata scartata per ora: aumenta costi di calcolo e complessità, e introduce errori di trascrizione che si propagherebbero al fact-checking. Potrà essere rivalutata con un ADR dedicato.

## Conseguenze
Copertura dei social incompleta, dichiarata pubblicamente come limite noto del sistema. Latenza realistica di minuti, sufficiente allo scopo. Ogni connettore va monitorato, perché i siti cambiano struttura e i feed si interrompono: servono controlli di salute per fonte e allarmi in caso di assenza di nuovi documenti.

La composizione del paniere va misurata con metriche di copertura per schieramento (ADR 0006). I costi residui si concentrano sulle chiamate agli LLM, e il filtro di perimetro è il principale strumento per contenerli. La mancanza di audio e video sottorappresenta chi comunica soprattutto in TV: va considerato nelle metriche di copertura.
