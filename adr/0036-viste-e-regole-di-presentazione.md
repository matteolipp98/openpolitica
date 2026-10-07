# ADR 0036 — Viste del prodotto e regole di presentazione

**Stato:** Proposto
**Attua:** ADR 0001, 0008, 0009, 0019, 0027, 0030

## Contesto
Gli ADR dicono cosa il sistema può affermare e cosa no, ma quelle regole si rispettano o si violano nell'interfaccia: è lì che un numero diventa un'accusa, che un ordinamento diventa una raccomandazione, che un'assenza di dato diventa un silenzio ambiguo.

Il pubblico è un elettore qualunque, senza competenze politiche o statistiche. Un'interfaccia corretta ma incomprensibile non protegge nessuno: la persona decide lo stesso, con meno informazioni.

## Decisione

### Le quattro viste della fase 0
**Indice dei soggetti** (`mockup/vista-soggetti.html`). Letture in cima generate da regole fisse uguali per tutti, poi una frase per soggetto e, aprendo, i singoli indicatori. Attua l'ADR 0019: ogni percentuale porta il proprio conteggio, sotto la soglia minima resta il conteggio assoluto, nessun indicatore sintetico.

**Questionario e risultato** (`mockup/vista-questionario.html`). Una domanda per schermata con una scheda di contesto prima della risposta (ADR 0013), calcolo nel browser (0007, 0008), graduatoria con pareggi dichiarati, discordanze sempre visibili e il caso "nessuno ti rappresenta" (0021).

**Scheda di un soggetto** (`mockup/vista-partito.html`). Posizioni per tema con il voto, la data e l'atto; promesse divise in mantenute, parziali e non mantenute (0020); confronti "ha detto / in realtà" (0014, 0030).

**Come funziona** (`mockup/vista-comefunziona.html`). Il metodo in quattro passaggi, un esempio applicato, la lista di cosa il sito fa e non fa, le domande scomode con risposta diretta. Attua l'ADR 0012: la credibilità si difende con la trasparenza, non con la dichiarazione di neutralità.

### Regole di presentazione, valide per ogni vista
**Linguaggio comune.** Niente termini tecnici o statistici: si scrive "sbaglia i numeri 14 volte su 72", non "tasso di imprecisione con intervallo di confidenza". Le frasi sono brevi e dirette, senza condiscendenza.

**Il conteggio accompagna sempre la percentuale**, e sotto la soglia la percentuale sparisce (0019).

**Ordinamenti neutri.** Nelle liste di soggetti l'ordine predefinito è alfabetico; ordinare per un indicatore è una scelta esplicita dell'utente (0009).

**L'assenza di dato è visibile e spiegata.** "Non si sa" accompagnato da "non inventiamo la loro posizione", mai una casella vuota (0027, 0030).

**Nessun verdetto, solo accostamenti.** Finché non c'è revisione umana vale l'ADR 0030: dichiarazione e dato ufficiale affiancati, nessuna etichetta di falsità. Il linguaggio resta descrittivo anche dopo: mai "ha mentito".

**Le discordanze sono obbligatorie.** Ogni risultato di affinità mostra anche dove non si è d'accordo (0009).

**Ogni affermazione è tracciabile.** Data, atto o serie statistica raggiungibili dal punto in cui compare il numero.

**Il confine fra fatti e valori è esplicito in pagina.** Ogni scheda chiude dicendo che sulla bontà delle idee decide il lettore (0001).

**Qualità minima.** Responsive fino al telefono, focus da tastiera visibile, tema chiaro e scuro, contrasto adeguato, nessuna animazione decorativa.

### Cosa gira a runtime
Le viste pubbliche sono pagine statiche su dati già calcolati: nessun modello interviene mentre l'utente naviga. Il calcolo dell'affinità gira nel browser. Gli unici punti con un modello a runtime sono la versione conversazionale del questionario e le spiegazioni generate, entrambe soggette a 0013 e 0015.

## Alternative considerate
Classifica unica di affidabilità in home: scartata (0009, 0019). Linguaggio tecnico con glossario: scartato, sposta sul lettore un lavoro che tocca a noi. Grafici ricchi al posto delle frasi: scartati, un numero dentro una frase viene letto, un grafico viene saltato.

## Conseguenze
I mock in `mockup/` sono la specifica visiva di riferimento, con dati inventati e segnalati come tali in pagina. Ogni modifica alle regole sopra è una modifica a un ADR, non una scelta di layout.
