# ADR 0036 — Viste del prodotto e regole di presentazione

**Stato:** Proposto
**Attua:** ADR 0001, 0008, 0009, 0019, 0027, 0030, 0037

## Contesto
Gli ADR dicono cosa il sistema può affermare e cosa no, ma quelle regole si rispettano o si violano nell'interfaccia: è lì che un numero diventa un'accusa, che un ordinamento diventa una raccomandazione, che un'assenza di dato diventa un silenzio ambiguo.

Il pubblico è un elettore qualunque, senza competenze politiche o statistiche. Un'interfaccia corretta ma incomprensibile non protegge nessuno: la persona decide lo stesso, con meno informazioni.

## Decisione

### Le quattro viste della fase 0
**Indice dei soggetti** (`mockup/vista-soggetti.html`). Letture in cima generate da regole fisse uguali per tutti, una per metrica, con i confronti tra soggetti ammessi dall'ADR 0037; poi una frase qualitativa per soggetto da soglie pubblicate e, aprendo, i singoli indicatori con un esempio "Ha detto / In realtà". Attua gli ADR 0019 e 0037: ogni percentuale porta il proprio conteggio, sotto la soglia minima resta il conteggio assoluto, nessun indicatore sintetico, elenco in ordine alfabetico.

**Questionario e risultato** (`mockup/vista-questionario.html`). Una domanda per schermata con una scheda di contesto prima della risposta (ADR 0013), tre risposte e la casella "conta più degli altri" (0037), calcolo nel browser (0007, 0008), graduatoria con pareggi entro un margine fisso, scomposizione per domanda con accordi, disaccordi e dati mancanti, e il caso "nessuno ti rappresenta" (0021).

**Scheda di un soggetto** (`mockup/vista-partito.html`). Riepilogo con i conteggi (numeri sbagliati, voti contrari a quanto dichiarato, promesse mantenute); posizioni per tema con il voto, la data e l'atto, e l'avviso quando parole e voto si contraddicono; promesse divise in mantenute, a metà e non mantenute, ciascuna con la motivazione (0020, 0037); confronti "ha detto / in realtà" (0014, 0037).

**Come funziona** (`mockup/vista-comefunziona.html`). Il metodo in quattro passaggi, un esempio applicato con il suo esito, la lista di cosa il sito fa e non fa, le domande scomode con risposta diretta. Attua l'ADR 0012: la credibilità si difende con la trasparenza, non con la dichiarazione di neutralità.

### Regole di presentazione, valide per ogni vista
**Linguaggio comune.** Il lettore è l'italiano medio, che non sa nulla di politica, statistica o fonti: ogni testo deve capirsi al primo colpo. Niente termini tecnici o statistici: si scrive "sbaglia i numeri 14 volte su 72", non "tasso di imprecisione con intervallo di confidenza". Le frasi sono brevi e dirette, senza condiscendenza. In pratica:

- una cosa per frase, possibilmente sotto le 15 parole;
- parole di tutti i giorni: mai "soglia", "denominatore", "definizione", "fonte di livello A", "metrica", "tolleranza", "modello", "serie";
- confronti concreti al posto delle quantità astratte: "il numero vero è meno della metà", non "scarto del 59%";
- il motivo di una regola si dice in una frase sola, e il dettaglio tecnico sta nella pagina di metodo, non nella vista;
- ogni testo nuovo si rilegge chiedendosi se lo capirebbe chi ha la terza media e non segue la politica: se no, si riscrive.

**Il conteggio accompagna sempre la percentuale**, e sotto la soglia la percentuale sparisce (0019).

**Ordinamenti neutri.** Nelle liste di soggetti l'ordine predefinito è alfabetico; ordinare per un indicatore è una scelta esplicita dell'utente (0009).

**L'assenza di dato è visibile e spiegata.** "Non si sa" accompagnato da "non inventiamo la loro posizione", mai una casella vuota (0027, 0030).

**Esiti in linguaggio comune, mai intenzioni.** Dichiarazione e dato ufficiale sono sempre affiancati; l'esito si scrive come "Numero sbagliato" con la ragione con un confronto concreto ("il numero vero è meno della metà"), alle condizioni dell'ADR 0037. Mai "ha mentito". "Fuorviante per contesto" non compare senza revisione umana.

**Le discordanze sono obbligatorie.** Ogni risultato di affinità mostra anche dove non si è d'accordo (0009).

**Ogni affermazione è tracciabile.** Data, atto o serie statistica raggiungibili dal punto in cui compare il numero.

**Il confine fra fatti e valori è esplicito in pagina.** Ogni scheda chiude dicendo che sulla bontà delle idee decide il lettore (0001).

**Qualità minima.** Responsive fino al telefono, focus da tastiera visibile, tema chiaro e scuro, contrasto adeguato, nessuna animazione decorativa.

### Cosa gira a runtime
Le viste pubbliche sono pagine statiche su dati già calcolati: nessun modello interviene mentre l'utente naviga. Il calcolo dell'affinità gira nel browser. Gli unici punti con un modello a runtime sono la versione conversazionale del questionario e le spiegazioni generate, entrambe soggette a 0013 e 0015.

## Alternative considerate
Classifica unica di affidabilità in home: scartata (0009, 0019); restano ammesse le letture per singola metrica dell'ADR 0037. Linguaggio tecnico con glossario: scartato, sposta sul lettore un lavoro che tocca a noi. Grafici ricchi al posto delle frasi: scartati, un numero dentro una frase viene letto, un grafico viene saltato.

## Conseguenze
I mock in `mockup/` sono la specifica visiva di riferimento, con dati inventati e segnalati come tali in pagina. Ogni modifica alle regole sopra è una modifica a un ADR, non una scelta di layout.
