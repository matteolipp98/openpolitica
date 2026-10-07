# ADR 0039 — Indicatori su annunci e promesse con Laya

**Stato:** Proposto
**Dettaglia:** ADR 0019, 0020, 0031, 0033, 0035, 0037; **modifica:** ADR 0038 (seconda famiglia per le decisioni chiuse)

## Contesto
Dalla fase 2 il sistema raccoglie ciò che i politici dicono fuori dall'aula: dichiarazioni, annunci, promesse (ADR 0002). Oggi su queste frasi produce due soli dati: i numeri sbagliati (0014) e la quota di frasi non controllabili (0019). Un elettore vuole sapere anche altro: se le promesse sono precise o generiche, se dicono dove si trovano i soldi, se a un annuncio segue qualcosa, quanto un partito parla delle sue proposte e quanto degli avversari.

Sono domande a cui si risponde classificando molte frasi brevi con poche scelte chiuse. È il compito per cui Laya è stato scelto (0031): risposte `choice`, `score`, `noul` in un solo passaggio, pesi aperti, nessun testo generato, costo per decisione quasi nullo. Il limite di Gemini (poche chiamate al giorno, 0038) rende comunque impossibile usare un modello generativo su migliaia di frasi al giorno.

Gli ADR 0020 e 0009 vietano però due scorciatoie: un voto di "realismo" dato da un modello e un punteggio unico che mescola cose diverse.

## Decisione

### Cosa si misura
Quattro indicatori nuovi, ciascuno una quota con numeratore e denominatore, calcolati per partito e per persona. Si aggiungono alle metriche dell'ADR 0019 e ne seguono tutte le regole.

| Indicatore | In pagina | Denominatore | Come si decide la singola frase |
|---|---|---|---|
| `promesse_precise` | "Promesse con un numero e una data" | promesse dette dal soggetto | Laya `noul`: "dice quanto" e "dice entro quando"; servono entrambi. Se nel testo non c'è nessuna cifra o data, la risposta è no senza chiedere al modello |
| `promesse_coperte` | "Promesse che dicono dove trovare i soldi" | promesse che richiedono spesa pubblica (Laya `noul`) | Laya `noul`: "indica come pagarla" (tagli, tasse, fondi europei, debito) |
| `annunci_seguiti` | "Annunci a cui è seguito un atto" | promesse e annunci con una scadenza già passata | Regola fissa: esiste un atto (legge, decreto, proposta depositata, voto) collegato e datato entro la scadenza. Il collegamento frase–atto richiede l'accordo di due famiglie (sotto) |
| `frasi_contro` | "Frasi contro gli avversari" | tutte le frasi attribuite al soggetto | Laya `choice` sul contenuto principale: proposta propria, bilancio di ciò che ha fatto, critica a un avversario, commento su un fatto |

Nessuno di questi giudica se una promessa è buona, giusta o realistica. Dicono com'è fatta la frase e cosa è successo dopo. Il realismo resta la scheda descrittiva dell'ADR 0020.

Il tipo di frase (promessa, annuncio, numero, critica, altro) si decide con una `choice` di Laya, a opzioni ruotate (0035). Le promesse dei programmi elettorali (fase 1) entrano negli stessi indicatori, contate a parte perché vengono da un documento e non da una dichiarazione.

### Regole sulle frasi che si contano
- Solo citazioni dirette e letterali, controllate nel testo della fonte (0015). Le frasi riportate da terzi non entrano.
- La classificazione avviene sul testo anonimizzato, con nomi e partiti sostituiti da segnaposto (0006): Laya non sa chi parla.
- Ogni decisione passa la soglia calibrata del suo tipo (0033). Le decisioni astenute non entrano né al numeratore né al denominatore, e il loro numero si mostra nella pagina di metodo ("su 412 frasi, 37 non le abbiamo sapute classificare").
- Paniere di fonti e finestra temporale uguali per tutti (0019, 0023). `frasi_contro` dipende molto dal canale: si calcola anche separato per tipo di fonte (aula, canali del partito, interviste), e la pagina mostra il dato complessivo solo se il paniere di ogni soggetto copre tutti i tipi.
- Denominatore minimo come per le altre metriche (`denominatoreMinimo`): sotto, solo il conteggio.
- `annunci_seguiti` dipende dal ruolo: chi governa può fare atti, chi è all'opposizione può solo proporli. Accanto al dato si dichiara il ruolo nel periodo (0019), e per l'opposizione conta come atto anche la proposta depositata.

### Laya come seconda famiglia, solo per le decisioni chiuse
L'ADR 0038 ha lasciato bloccato tutto ciò che chiede l'accordo tra due famiglie di modelli. Laya è un modello di un'altra famiglia (encoder, addestramento diverso, nessuna generazione). Per le **decisioni chiuse**, in cui due modelli scelgono tra le stesse opzioni, l'accordo tra Gemini e Laya vale come accordo tra famiglie:

- collegamento tra promessa e atto (0037, stato delle promesse; `annunci_seguiti`);
- tema e direzione degli enunciati del catalogo (0030), come verifica aggiuntiva della chiamata cieca dell'ADR 0038.

Non vale per l'estrazione dell'interrogazione strutturata di un numero (metrica, periodo, territorio, unità), che è un testo aperto: lì restano necessarie due famiglie generative, e gli esiti negativi del fact-checking restano bloccati come dice l'ADR 0038.

Vale solo dopo che il checkpoint di Laya usato ha superato il controllo dell'ADR 0033 sul golden set italiano per quel tipo di decisione. Prima, Laya lavora in laboratorio (0016) e i suoi risultati non si pubblicano.

### Cosa si vede
Ogni indicatore è una riga a sé nella scheda del soggetto, con cifra, frase in linguaggio comune e conteggio sotto, come le altre righe (0036, 0037). Le frasi qualitative ("di solito precise", "quasi mai dicono dove trovare i soldi") e le letture comparative dell'indice ("X è quello che fa più promesse senza data") seguono le regole dell'ADR 0037: una metrica per lettura, soglie scritte in `content/letture.yaml`, pari merito nominati tutti. Si vede anche come cambiano nel tempo (ADR 0040).

### Versioni
Le domande tipizzate di ogni indicatore vivono in `content/domande-laya/` con versione (0035). Ogni dato pubblicato porta checkpoint di Laya, versione delle domande e versione della calibrazione. Cambiare una domanda ricalcola l'indicatore per tutti i soggetti e per tutto il periodo, mai solo da una data in poi.

## Alternative considerate
**Un punteggio di qualità delle promesse da 0 a 100:** scartato, mescola precisione, copertura e seguito, e il peso tra loro è una scelta di valore (0009, 0019). **Far giudicare a Laya se una promessa è realistica:** scartato per le stesse ragioni dell'ADR 0020. **Usare Gemini per classificare le frasi:** scartato, le chiamate giornaliere non bastano per una frazione dei volumi e il testo delle fonti di livello C non deve uscire verso terzi più del necessario (0003). **Contare solo le promesse dei programmi:** scartato, gli annunci in corso di legislatura sono quelli che l'elettore sente davvero.

## Conseguenze
La fase 2 diventa utile per l'elettore anche prima del fact-checking. Il golden set dell'ADR 0033 deve coprire anche queste quattro decisioni, con etichette fatte da persone di orientamento diverso: è il prerequisito reale, perché senza calibrazione non si pubblica nulla. `frasi_contro` è l'indicatore più esposto a contestazioni: il metodo e il campione etichettato vanno pubblicati insieme al dato. Laya come seconda famiglia sblocca lo stato delle promesse senza revisione umana, ma è un controllo più debole di due famiglie generative indipendenti: la decisione aperta 3 del piano (terza famiglia) resta valida.
