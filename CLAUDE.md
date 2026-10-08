# openpolitica

App pubblica che aiuta i cittadini a valutare i politici italiani: fatti uguali per tutti, valori dell'utente. Le decisioni sono in `adr/` (indice in `adr/README.md`), il piano di implementazione in `docs/piano-implementazione.md`.

## Regole di lavoro

- **Il lettore è l'italiano medio, senza nessuna competenza politica o statistica.** Ogni testo visibile (mock, viste, FAQ, messaggi) deve capirsi al primo colpo: frasi corte, una cosa per frase, parole di tutti i giorni, confronti concreti ("meno della metà") invece di percentuali e termini tecnici. Il dettaglio tecnico va nella pagina di metodo. Regole complete nell'ADR 0036, "Linguaggio comune".
- Tutto in italiano: ADR, piano, commenti nei mock, messaggi di commit.

## Esperienza del sito: come dovevannoinostrisoldi.com

L'esperienza del sito deve somigliare a quella di [dovevannoinostrisoldi.com](https://www.dovevannoinostrisoldi.com/) (decisione dell'utente, 8 ottobre 2026). Vale per ogni mock, vista e componente nuovi. Si riprende la struttura e il modo di presentare i dati, non i contenuti. Quando si progetta una pagina si apre il sito e si guarda come risolve un caso simile. Le pagine più vicine alle nostre sono:
- [`/programmi`](https://www.dovevannoinostrisoldi.com/programmi): le promesse dei programmi messe di fronte ai numeri ufficiali;
- [`/governi`](https://www.dovevannoinostrisoldi.com/governi): la "pagella" di ogni governo, con i grafici nel tempo;
- [`/politici`](https://www.dovevannoinostrisoldi.com/politici): la mappa di chi siede in Governo, Camera e Senato;
- [`/palazzo-chigi`](https://www.dovevannoinostrisoldi.com/palazzo-chigi): un buon esempio di numero grande, nota che spiega e blocco "Fonte e controlli".

Cosa si riprende:
- **Un blocco, un dato.** Ogni blocco è una scheda bianca con bordo sottile su fondo chiaro. In alto c'è un'etichetta piccola in maiuscolo con un "?" che apre la spiegazione. Sotto c'è un numero grande, con una frase che dice cosa conta, dove e in che periodo. Poi qualche riga con i dettagli: nome a sinistra, valore a destra.
- **Fonte e data su ogni blocco.** In fondo alla scheda c'è sempre la riga "Fonte: … · aggiornato al …", con il link alla fonte ufficiale. Sotto, una voce che si apre ("Dati esatti e fonte") con la tabella dei valori esatti.
- **Barre orizzontali con il valore accanto.** Il nome sopra la barra, il numero sotto il nome, il valore a destra. Si ordinano per valore, salvo dove i nostri ADR chiedono l'ordine alfabetico (partiti e persone, ADR 0009).
- **Note che evitano gli equivoci**, subito sotto il dato, in una frase: "Settembre è a metà: il numero può cambiare", "Non dimostra che abbia mentito: va controllato". Il dato non ancora completo si mostra in grigio.
- **Scelte con bottoni affiancati** (anno, Camera/Senato, tema), non con menu a tendina, quando le scelte sono poche.
- **Home come indice:** titolo e una frase che dice cosa c'è nel sito, una ricerca ben visibile, schede delle sezioni con titolo, una riga di descrizione e "Apri ›". Poi i blocchi con i dati principali.
- **Cosa facciamo e cosa non facciamo**, detto in chiaro su ogni sezione nuova o non ancora pronta. Se una sezione non è pronta si dice quando arriva e cosa si può vedere intanto.
- Un solo colore di richiamo per link e bottoni, menu laterale con icone, tema chiaro e scuro, pagine che funzionano bene sul telefono.

Cosa non si riprende, perché valgono le nostre regole:
- **Percentuali da sole e numeri tecnici.** Il sito ne usa molti. Da noi valgono il linguaggio comune (ADR 0036) e il conteggio accanto a ogni numero (ADR 0019): "11 volte su 96", non "11,5%".
- **Colori dei partiti, classifiche e voti in centesimi.** La pagella dei governi dà un voto come "62/100": da noi no. Colori neutri in ordine alfabetico e nessun punteggio unico (ADR 0009).
- **Giudizi.** Mostriamo cosa hanno detto e cosa hanno fatto, non se è giusto (ADR 0001).

Se un'idea del sito va contro un ADR, vince l'ADR, oppure si propone di cambiare l'ADR.

## Board e flusso di lavoro (scrum)

Il lavoro si segue sulle issue di GitHub di `matteolipp98/openpolitica`, mostrate come board nel GitHub Project del repository. **Ogni sviluppo parte da un'issue e la board va tenuta aggiornata a ogni passo.**

- **Etichette.**
  - Stato: `da-fare`, `in-corso`, `bloccato`; un'issue chiusa è fatta.
  - Sprint: `sprint-N` per lo sprint corrente, `backlog` per il resto.
  - Fase: `fase-0` … `fase-5`, `trasversale`.
  - Area: `dati`, `catalogo`, `sito`, `modelli`, `contenuti`, `manutenzione`, `decisione`.
  - Le fasi sono issue con etichetta `epica` e contengono la lista dei loro task.
- **Primo passo di ogni sessione:** `git pull --ff-only origin main` nella cartella principale, da solo, prima di leggere lo stato, le issue o i file. Così non si lavora su una copia vecchia.
- **Stato condiviso:** l'issue con etichetta `stato` ("📌 Stato del progetto", #53) non si chiude mai. Si legge **all'inizio di ogni sessione**, subito dopo il pull, e si **riscrive alla fine** (o quando cambia qualcosa di importante). Contiene: dove siamo, cosa sta girando adesso, decisioni prese, cosa serve dall'utente, prossimi passi. Si aggiorna la riga "Aggiornato:" con data e ora. Le decisioni dell'utente prese in chat si scrivono subito lì, così non si perdono tra una sessione e l'altra.
- **Prima di iniziare:** leggere le issue aperte dello sprint corrente e prendere la prima `da-fare` non bloccata, oppure quella che chiede l'utente. Le issue `in-corso` sono già prese da qualcuno: non si toccano. Se il lavoro richiesto non ha un'issue, crearla prima, con l'elenco "Fatto quando".
- **`in-corso` subito, prima di cominciare** (decisione dell'utente, 8 ottobre 2026). Un'issue si mette `in-corso` al posto di `da-fare` nel momento in cui la si prende: prima di creare il worktree, prima di leggere il codice, prima di lanciare un agente. Così chi guarda la board sa che è già presa e non la fa in parallelo. Vale anche per le issue date a un agente e per quelle in coda allo stesso agente, che si segnano tutte insieme al momento del lancio. Se un'issue non si fa più, si toglie `in-corso` e si rimette `da-fare`, con un commento che dice perché.
- **Durante:** commento breve sull'issue quando c'è qualcosa da ricordare (una misura, un problema trovato, una scelta). Se viene fuori lavoro nuovo si apre un'altra issue, non si allarga quella in corso.
- **Alimentare la board, sempre.** Ogni bug, problema, idea di miglioramento o lavoro rimasto a metà che non si risolve subito diventa un'issue nel momento in cui lo si trova, prima di passare ad altro. Va bene anche un'issue piccola: titolo chiaro, cosa succede, "Fatto quando", etichette di fase, area e `backlog`. Vale per tutto quello che si nota lavorando: codice, dati, testi, sito, workflow, documentazione. Nulla di quello che si è visto deve restare solo nella conversazione. A fine sessione, prima di aggiornare lo stato (#53), si ricontrolla di non aver lasciato fuori niente.
- **Alla fine:** il commit cita l'issue (`#N`, oppure `closes #N`: GitHub chiude da solo solo con le parole inglesi, non con "chiude"). Si spuntano i criteri "Fatto quando" e si chiude l'issue con un commento: cosa è stato fatto e come è stato verificato. Si aggiorna la lista nell'epica.
- **Se è bloccata:** etichetta `bloccato` e commento con cosa manca. Se serve l'utente, una riga che inizia con "Serve da te:".
- **Sprint di una settimana.** A fine sprint, le issue non finite passano allo sprint successivo e lo sprint nuovo si riempie dal backlog in ordine di fase.
- **Niente pull request da revisionare.** Si lavora sul branch di sviluppo, si fanno i controlli locali, si aspetta la CI verde sul branch e si porta il commit in `main` direttamente. Lo stesso per i job automatici, come il catalogo.
- **Un task, un worktree (in locale).** Quando si lavora in locale, ogni issue si sviluppa in un suo git worktree, con un suo branch nato da `main` aggiornato, così più task possono andare avanti in parallelo senza toccarsi:
  - `git fetch origin && git worktree add ../openpolitica-<N> -b task/<N>-<breve> origin/main` (N = numero dell'issue);
  - si lavora e si fanno i controlli solo dentro quel worktree, con commit che citano `#N`;
  - per chiudere: `git rebase origin/main`, controlli di nuovo verdi, poi in `main` (`git push origin HEAD:main`, cioè un avanzamento lineare) e `git worktree remove ../openpolitica-<N>` più la cancellazione del branch;
  - mai due issue nello stesso worktree; se durante il lavoro ne nasce un'altra, si apre l'issue e la si sviluppa in un worktree suo.
  Nelle sessioni nel cloud, dove il branch di lavoro è assegnato, si lavora su quel branch e si porta in `main` un task alla volta.
- Commenti e issue scritti da Claude finiscono con la riga `_Generated by [Claude Code](https://claude.ai/code)_`.
