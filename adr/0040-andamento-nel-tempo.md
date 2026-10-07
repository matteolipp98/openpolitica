# ADR 0040 — Andamento dei partiti nel tempo

**Stato:** Proposto
**Dettaglia:** ADR 0019, 0023, 0036, 0037, 0039

## Contesto
Le metriche dell'ADR 0019 e gli indicatori dell'ADR 0039 oggi sono una fotografia: un numero per soggetto sulla finestra corrente. L'elettore si chiede anche se un partito è cambiato: se sbaglia meno numeri di un anno fa, se da quando è al governo fa promesse più vaghe, se all'opposizione vota sempre contro.

Una serie nel tempo è anche il modo più facile per far dire ai dati quello che non dicono: denominatori piccoli per periodo, curve lisciate che inventano una tendenza, finestre scelte per far vedere un calo, partiti confrontati su periodi diversi.

## Decisione

### Cosa si mostra
Una pagina "Com'è cambiato nel tempo" e, nella scheda di ogni partito, una sezione con le stesse serie per quel partito.

- **Una metrica per grafico.** Si sceglie la metrica; si vede un piccolo grafico per ogni partito, in ordine alfabetico, tutti con la stessa scala e lo stesso periodo. Nessun grafico mette insieme due metriche, nessun indice composto (0009, 0019).
- **Periodo: il trimestre.** Ogni punto è un trimestre solare con il suo numeratore e il suo denominatore, leggibili toccando il punto.
- **Pochi dati, nessun punto.** Se in un trimestre il denominatore è sotto `denominatoreMinimo`, il punto non c'è e la linea si interrompe. Non si unisce mai un buco con una linea.
- **Niente curve inventate.** Niente medie mobili, linee di tendenza, previsioni o interpolazioni: punti veri uniti da segmenti (0023).
- **Il ruolo si vede.** I periodi al governo sono una fascia di sfondo, presa da `content/partiti.yaml`. Elezioni e cambi di governo sono segni sull'asse del tempo. Chi passa dal governo all'opposizione cambia quasi tutti gli indicatori, e il lettore deve vederlo subito.
- **Scala in parole.** L'asse verticale va da "nessuna" a "tutte", con "metà" in mezzo. Le percentuali stanno nel dettaglio del punto, sempre con il conteggio (0036).
- **Le persone dopo.** Per le singole persone i denominatori per trimestre sono quasi sempre sotto la soglia: la serie delle persone si mostra solo dove la soglia è raggiunta in almeno quattro trimestri, altrimenti non compare.

### La frase sopra il grafico
Ogni grafico ha una frase in linguaggio comune che confronta **gli ultimi quattro trimestri con i quattro precedenti**, sommando numeratori e denominatori:

- "più di prima" o "meno di prima" solo se la differenza supera il rumore statistico: gli intervalli di confidenza al 95% dei due anni (Wilson) non si sovrappongono;
- altrimenti "più o meno come prima";
- se uno dei due anni è sotto soglia, "non abbiamo abbastanza dati per dire se è cambiato".

La frase riporta sempre i due conteggi ("31 volte su 100 nell'ultimo anno, 22 su 100 l'anno prima"). Non dice mai "migliora" o "peggiora": se sia meglio votare compatti o con il governo lo decide il lettore (0001). La regola e i testi stanno in `content/letture.yaml`, versionati.

### Metriche disponibili da subito
Due metriche vengono solo dai voti, si calcolano dai conteggi per gruppo (`core.votazione_gruppo`) senza nessun modello, e si possono pubblicare già nella fase 0:

| Metrica | In pagina | Come si calcola |
|---|---|---|
| `vota_con_governo` | "Vota come il governo" | votazioni finali in cui la maggioranza dei votanti del gruppo vota come la maggioranza dei votanti dei gruppi di governo, sul totale delle votazioni finali in cui il gruppo ha almeno `membriMinimi` votanti |
| `vota_compatto` | "Vota compatto" | votazioni in cui almeno 9 votanti del gruppo su 10 votano allo stesso modo, sullo stesso denominatore |

Per un partito di governo `vota_con_governo` è vicino a "tutte" per costruzione: la pagina lo dice invece di nasconderlo. Le presenze in aula non si mostrano: i conteggi per gruppo oggi mettono insieme assenti, in missione e presidenza (`altri`), e non si può separare chi manca senza motivo. Servirà una colonna in più nella tabella.

Le altre serie arrivano quando arriva la loro metrica: numeri sbagliati e frasi non controllabili con le fasi 2 e 3, i quattro indicatori dell'ADR 0039 con la calibrazione di Laya, i voti al contrario di quanto detto quando le posizioni da dichiarazioni sono pubblicabili. Le metriche non ancora disponibili compaiono nell'elenco con la frase "Arriva quando…", come nelle schede.

### Dati
Il pacchetto di rilascio contiene `andamento.json`: per soggetto, metrica e trimestre, numeratore, denominatore e versione del calcolo. Le serie si ricalcolano da capo a ogni rilascio, per tutto il periodo e per tutti i soggetti. Una correzione cambia il passato con una nuova versione, senza cancellare la precedente (0005, 0023). Il grafico è un SVG disegnato dalla pagina, con una tabella equivalente per chi usa un lettore di schermo.

## Alternative considerate
**Un grafico con tutti i partiti sovrapposti:** scartato, otto linee incrociate non si leggono su un telefono e invitano alla classifica. **Mese invece di trimestre:** scartato, troppi punti sotto soglia. **Media mobile per avere linee più lisce:** scartata, crea tendenze che i dati non hanno. **Frase "migliora / peggiora":** scartata, è un giudizio di valore (0001).

## Conseguenze
La prima versione della pagina esce con due metriche sui voti, utili soprattutto per vedere l'opposizione, e si riempie man mano che le fasi successive arrivano. Il confronto tra anni rende visibili i cambi di metodo: ogni cambio di versione di una metrica ricalcola tutta la serie, e la pagina di metodo elenca le versioni.
