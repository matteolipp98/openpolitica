# ADR 0022 — Catalogo degli enunciati

**Stato:** Proposto, modificato da ADR 0030 (modalità automatica iniziale)

## Contesto
Gli enunciati sono le domande su cui si confrontano utente e politici. Sono l'asset più importante e più politico del progetto: quali temi entrano, quanti enunciati per tema e come sono formulati determinano il risultato molto più di qualsiasi scelta di modello. Un catalogo sbilanciato produce un sistema sbilanciato anche con una pipeline perfetta.

## Decisione
**Copertura bilanciata.** Un numero fisso e uguale di enunciati per ciascun tema della tassonomia, così che nessuna area pesi di più per semplice numerosità. L'importanza relativa la decide l'utente con i pesi, non il catalogo.

**Criteri di formulazione.** Ogni enunciato è una posizione concreta su una misura, non un valore astratto; è formulato in modo che sia plausibile essere sia a favore sia contrari; usa un linguaggio neutro senza termini connotati; riguarda una sola cosa, senza congiunzioni che nascondano due questioni; è discriminante, cioè i partiti non hanno tutti la stessa posizione; è ancorabile, cioè esiste almeno un voto parlamentare o una posizione documentata che permetta di collocarvi i soggetti.

**Processo.** Proposta redazionale, revisione del panel pluralista (ADR 0012), test di formulazione con lettori di orientamenti diversi, approvazione e versionamento. Ogni modifica è tracciata; i profili utente registrano la versione del catalogo su cui sono stati compilati.

**Manutenzione.** Revisione periodica, aggiunta di enunciati quando emergono questioni nuove, ritiro di quelli superati con storicizzazione delle posizioni già raccolte. Un enunciato che risulta non discriminante o poco ancorabile viene riscritto o ritirato.

**Ancoraggio ai voti.** Per ogni enunciato si cura a mano l'elenco delle votazioni pertinenti con la direzione (favorevole o contrario). Questa mappatura è pubblica, è la parte che determina più di ogni altra i risultati ed è rivista dal panel.

**Test di equilibrio.** Prima di ogni pubblicazione si verifica che il catalogo non favorisca sistematicamente un'area: si simulano profili utente uniformi e si controlla che la distribuzione delle affinità non sia sbilanciata per costruzione.

## Alternative considerate
Enunciati generati da un modello: utili come bozza, mai come catalogo, perché ereditano il bias del modello sul framing. Assi ideologici astratti al posto degli enunciati: scartati, gli assi sono contestati e comprimono le posizioni reali.

## Conseguenze
Lavoro manuale considerevole, circa 30 enunciati nell'MVP con la relativa mappatura dei voti, ed è il lavoro che determina la qualità del prodotto. Le versioni del catalogo rendono i risultati confrontabili nel tempo solo a parità di versione, e l'interfaccia deve dirlo.
