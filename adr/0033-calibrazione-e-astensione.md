# ADR 0033 — Calibrazione, soglie di confidenza e astensione

**Stato:** Proposto
**Dettaglia:** ADR 0031, condiziona ADR 0008

## Contesto
Diversi ADR usano la confidenza del modello come se fosse una probabilità affidabile: la posizione su un enunciato si registra solo sopra una soglia (0008), il delta controfattuale si misura su probabilità (0016), la validazione delle frasi decide su una probabilità (0015).

I checkpoint Laya sono sovra-confidenti così come distribuiti, e il checkpoint multilingue — quello che serve l'italiano — non ha temperature calibrate. Una soglia scelta a occhio su numeri non calibrati è peggio che non avere soglia, perché dà una falsa sensazione di controllo.

## Decisione
**Niente soglie prima della calibrazione.** Nessuna soglia di confidenza entra in produzione prima che le temperature siano state stimate su dati italiani etichettati del dominio e validate su un insieme separato.

**Dataset di calibrazione.** Un campione stratificato di claim e voti italiani etichettati a mano, per tipo di domanda e numero di opzioni. È lo stesso golden set dell'ADR 0006 e serve a tre scopi: calibrare, misurare e, se necessario, adattare (ADR 0034).

**Calibrazione per bucket.** Le temperature si stimano separatamente per combinazione di tipo di domanda e numero di opzioni, perché una soglia non si trasferisce tra numeri di opzioni diversi. Dove la curva di affidabilità non si corregge con la sola temperatura, si usa una ricalibrazione a istogramma.

**Metriche di accettazione.** Errore di calibrazione atteso, Brier, accuratezza selettiva e accuratezza alla copertura scelta. Le soglie si leggono da queste curve: si sceglie il punto in cui gli errori accettati sono sostenibili, non un numero tondo.

**Astensione esplicita.** Ogni decisione dichiara se la soglia è stata applicata e con quale esito: superata, astenuta, o non valutabile. Le decisioni astenute non diventano posizioni pubblicate: finiscono in coda di ispezione, oppure semplicemente non producono dato (ADR 0008).

**Quantità misurate, non assunte.** La soglia si applica alla probabilità della risposta riportata, non a misure di entropia, e va rifissata se cambiano checkpoint, precisione numerica o numero di opzioni. Il tasso di astensione è una metrica di prodotto monitorata.

**Gate automatico.** La suite di valutazione dell'ADR 0025 verifica calibrazione e accuratezza a ogni modifica di modello, prompt o tassonomia, e blocca il rilascio se peggiorano.

## Alternative considerate
Usare le confidenze così come escono: scartato, sono sovra-confidenti e in una app elettorale produrrebbero posizioni attribuite a torto. Rinunciare alle soglie e pubblicare tutto: scartato, l'ADR 0027 impone di non attribuire in caso di incertezza.

## Conseguenze
Serve lavoro umano di etichettatura prima della fase 2, ed è il prerequisito reale di tutta la parte automatica. Il golden set diventa l'asset più riusato del progetto: calibra, valuta, misura il bias e serve all'eventuale adattamento.
