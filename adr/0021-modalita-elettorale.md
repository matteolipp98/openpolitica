# ADR 0021 — Oggetto del voto e modalità elettorale

**Stato:** Proposto

## Contesto
Finora il sistema ragiona su politici e partiti, ma sulla scheda si vota altro. Alle politiche si esprime un voto che coinvolge il candidato nel collegio uninominale e la lista, dentro coalizioni, con soglie di sbarramento e liste bloccate. Un partito molto affine può inoltre stare in una coalizione il cui programma comune è lontano dall'utente.

Inoltre in campagna elettorale cambia tutto: i programmi arrivano poche settimane prima, l'attenzione è massima e la pressione sul sistema pure.

## Decisione
**Tre oggetti di affinità.** L'affinità viene calcolata e mostrata separatamente per partito, per programma di coalizione e, quando i dati esistono, per il candidato del collegio dell'utente. Non si fondono: se il partito è affine ma la coalizione no, l'utente deve vederlo.

**Collegio.** Un modulo converte il comune o il CAP indicato dall'utente nel collegio corrispondente e mostra i candidati. Il dato di localizzazione resta sul client come il resto del profilo (ADR 0007).

**Meccanica elettorale.** L'app spiega in modo neutro e uguale per tutti le regole che influenzano l'effetto del voto: soglie di sbarramento, liste bloccate, assenza di voto disgiunto. È informazione fattuale sulle regole, non un consiglio di voto utile: non si suggerisce mai un voto strategico.

**Nessuno ti rappresenta.** Se l'affinità massima resta bassa, il sistema lo dice esplicitamente invece di forzare un vincitore, e descrive in modo neutro le opzioni disponibili, incluse astensione e scheda bianca, con i loro effetti sul risultato.

**Livelli di governo.** Ogni enunciato è etichettato con il livello competente. In una consultazione europea o regionale si mostrano solo gli enunciati di competenza di quel livello, per non valutare un candidato su materie che non potrà toccare. L'MVP copre le politiche.

**Modalità campagna.** Dalla convocazione dei comizi: metodologia congelata, nessun cambio di enunciati, prompt, modelli o algoritmo; procedura accelerata per l'analisi dei programmi depositati con revisione umana rafforzata; log delle pubblicazioni; verifica preventiva degli obblighi applicabili in tema di par condicio e silenzio elettorale (ADR 0010); monitoraggio delle anomalie nelle fonti, per esempio picchi improvvisi di dichiarazioni moderate su canali ufficiali.

**Continuità di servizio.** Durante la campagna il questionario e il calcolo dell'affinità devono funzionare anche senza modelli: sono deterministici e lato client. Se i fornitori di LLM non sono disponibili, chat e spiegazioni si degradano a testi a template, il resto resta in piedi.

## Alternative considerate
Affinità solo di partito: più semplice ma non corrisponde alla scheda. Suggerire il voto utile date le soglie: scartato, è un consiglio politico e non un fatto.

## Conseguenze
Serve il dataset dei collegi e dei candidati, disponibile solo a ridosso del voto, e una mappatura comune-collegio da mantenere. Nell'MVP l'affinità resta a livello di partito e coalizione, con il collegio come estensione successiva.
