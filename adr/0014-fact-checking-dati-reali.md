# ADR 0014 — Fact-checking basato su dati reali e calcoli deterministici

**Stato:** Proposto
**Estende:** ADR 0004 (stadi 4 e 5)

## Contesto
Il valore distintivo dell'app è riportare il dibattito ai dati: verificare i numeri citati dai politici, stimare cosa costano le proposte, mostrare il contesto che viene omesso. È anche il punto in cui un errore costa di più, in credibilità e sul piano legale. Un LLM che "ricorda" un dato o calcola a mente una percentuale non è accettabile.

## Decisione
**I numeri non vengono mai prodotti da un LLM.** L'LLM traduce un claim in una interrogazione strutturata; il dato arriva da una fonte ufficiale; il confronto è un calcolo deterministico.

Il flusso per un claim quantitativo è il seguente. L'LLM estrae dal claim metrica, unità, periodo, territorio, popolazione di riferimento e tipo di confronto (livello, variazione, confronto internazionale). Un catalogo di indicatori mappa la metrica alla serie ufficiale: ISTAT tramite API SDMX, Eurostat, Banca d'Italia, UPB, Ragioneria Generale dello Stato e OpenBDAP, INPS, ministeri. Un servizio di calcolo recupera la serie e confronta il valore dichiarato con quello ufficiale secondo regole di tolleranza pubblicate. Se la metrica è ambigua (per esempio disoccupazione con definizioni diverse) si confronta con tutte le definizioni plausibili e lo si dichiara.

Gli esiti sono: supportato, impreciso, fuorviante per contesto (dato corretto ma periodo o confronto scelti ad arte), contraddetto, non verificabile. L'esito "fuorviante per contesto" richiede la regola che lo giustifica (per esempio serie cherry-picked rispetto a una finestra standard) e revisione umana.

**Costi e coperture delle proposte.** Si usano solo stime ufficiali o terze e citabili: relazioni tecniche, UPB, Corte dei conti, osservatori riconosciuti. Se non esiste una stima, l'app scrive "costo non stimato da fonti ufficiali" e non produce stime proprie. Lo stesso vale per le coperture dichiarate.

**Schede di contesto.** Per ogni tema il panel definisce un set stabile di indicatori di base (per esempio debito, occupazione, spesa pensionistica, emissioni) mostrati con serie storiche e stessa finestra temporale per tutti i politici, così il contesto non viene scelto in funzione di chi parla.

**Coerenza nel tempo.** Il sistema confronta dichiarazioni e voti dello stesso politico e segnala cambi di posizione con le date e le evidenze, senza qualificarli.

**Benchmark esterno.** Gli esiti vengono confrontati periodicamente con quelli di fact-checker indipendenti firmatari del codice IFCN attivi in Italia, sugli stessi claim. Il disaccordo sistematico viene analizzato e pubblicato. Gli esiti sono esportati in formato ClaimReview.

## Alternative considerate
Verifica tramite LLM con retrieval testuale: scartata per i claim quantitativi, ammessa solo per claim fattuali non numerici (per esempio "la legge X è stata approvata"), con fonte obbligatoria. Stime di costo generate dal sistema: scartate perché trasformerebbero l'app in un soggetto che produce previsioni contestabili.

## Conseguenze
Il catalogo di indicatori e le regole di tolleranza diventano asset curati e versionati, con manutenzione continua. Molti claim risulteranno "non verificabili": è un risultato corretto e va mostrato, perché anche la non verificabilità è un'informazione utile per l'elettore. Il carico di revisione umana si concentra sugli esiti "contraddetto" e "fuorviante per contesto".
