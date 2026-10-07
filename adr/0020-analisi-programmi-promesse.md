# ADR 0020 — Analisi dei programmi e realismo delle promesse

**Stato:** Proposto

## Contesto
I programmi elettorali sono il documento su cui si decide il voto e nessuno li legge. Sono pochi, finiti e disponibili dal 2018 sul portale del Ministero dell'Interno, quindi sono il corpus ideale da analizzare per primo. La domanda dell'utente è se le promesse siano realistiche, ma un sistema che dichiara "irrealistica" emette una previsione contestabile e si espone.

## Decisione
Si scompone invece di giudicare. Ogni promessa diventa un oggetto strutturato con misura, beneficiari, orizzonte temporale, strumento normativo necessario, livello di competenza, costo dichiarato e copertura indicata. Su questo si applicano cinque test verificabili.

**1. Quantificazione.** La promessa ha numeri e scadenza? Se no è non verificabile, ed è già un'informazione da mostrare.

**2. Ordine di grandezza.** Se esiste una stima di costo ufficiale o di terzi citabile (relazione tecnica, UPB, Corte dei conti), la si rapporta ad aggregati di bilancio: quota della spesa del settore, del PIL, del gettito. È aritmetica su dati ufficiali, non una previsione.

**3. Copertura.** È indicata una fonte di finanziamento, e qualcuno l'ha valutata?

**4. Vincoli di attuabilità.** Serve una legge costituzionale, è materia di competenza UE, è competenza regionale, esiste una pronuncia della Corte costituzionale che la limita. È una tassonomia con riferimenti normativi, non un'opinione.

**5. Ricorrenza storica.** La stessa promessa compare nei programmi precedenti dello stesso partito? Se sì, si mostra da quando, e se nel frattempo sono stati presentati atti coerenti.

L'output è una scheda descrittiva, non un voto di realismo. Esempio di forma: promessa non quantificata, costo stimato dall'UPB pari a una certa quota della spesa del settore, nessuna copertura indicata, richiede modifica costituzionale, presente in forma identica dal 2018.

**Nessuna stima propria.** Se una stima ufficiale non esiste, la scheda dice che il costo non è stato stimato da fonti ufficiali (ADR 0014).

**Collegamento al resto.** Ogni promessa è collegata agli enunciati (per l'affinità) e diventa un oggetto tracciabile nel tempo: atti presentati, voti, attuazione (ADR 0019).

## Alternative considerate
Punteggio di realismo generato da un modello: scartato, è una previsione non verificabile e legalmente esposta. Stime di costo prodotte dal sistema: scartate per lo stesso motivo. Analisi solo qualitativa del testo: scartata, non permette confronti tra partiti.

## Conseguenze
Il lavoro di estrazione è pesante ma concentrato: pochi documenti, poche settimane prima del voto. Serve una procedura di campagna che permetta di processare e revisionare i programmi in pochi giorni (ADR 0021). Il test 5 richiede l'archivio dei programmi storici, che va costruito una volta sola.
