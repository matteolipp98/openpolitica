# ADR 0038 — Gemini come unico fornitore di modelli iniziale

**Stato:** Proposto
**Modifica:** ADR 0016, 0017, 0030

## Contesto
Per partire il progetto ha a disposizione un solo fornitore di modelli generativi, Google Gemini, con un numero di chiamate giornaliere molto basso. Gli ADR prevedono invece OpenAI e Anthropic dietro LiteLLM (0017) e, nel job che genera il catalogo, l'**accordo tra due famiglie di modelli** come controllo sostitutivo della revisione umana (0030): una famiglia propone tema e direzione di ogni domanda, l'altra conferma.

Con una sola famiglia quel controllo non esiste. Fingere che esista, per esempio chiamando due volte lo stesso modello e parlando di "accordo", sarebbe peggio che dichiararne l'assenza.

## Decisione

**Gemini per il catalogo, chiamato direttamente.** Il job di catalogo usa la API di Gemini senza passare dal gateway LiteLLM, che non è ancora in esercizio. Il modello è fissato per nome con versione e registrato in ogni run (0016).

**Cosa sostituisce, per ora, il secondo modello.** Generazione e verifica sono due chiamate separate, con istruzioni diverse e senza memoria comune:

1. la prima propone tema, domanda, forma opposta, due riformulazioni e le frasi di contesto;
2. la seconda riceve solo il titolo dell'atto e le frasi mescolate, senza sapere quale sia l'originale né quale direzione sia stata proposta, e per ciascuna dice se chi ha votato sì è d'accordo; sceglie anche il tema da un elenco in ordine diverso.

Una domanda entra nel catalogo solo se la verifica conferma tema e direzione dell'originale e delle riformulazioni, e dà la direzione opposta per la forma opposta (test di sensibilità e di polarità dell'ADR 0030, giudicati dalla seconda chiamata). È un controllo più debole dell'accordo tra famiglie, perché lo stesso modello porta lo stesso bias in entrambe le chiamate, e va dichiarato.

**Catalogo provvisorio.** Il catalogo generato così porta `stato: provvisorio`. La pagina di metodo lo dice in linguaggio comune: le domande sono state scritte e controllate da un solo sistema di intelligenza artificiale. Quando sarà disponibile una seconda famiglia di modelli, la verifica si ripete con quella prima che il catalogo diventi definitivo; le domande che non la superano vengono ritirate, con storicizzazione (0022).

**Poche chiamate.** Le votazioni vanno al modello a lotti (decine per chiamata). Ogni risposta si salva in una cache nel repository prima di proseguire, così un job interrotto per esaurimento delle chiamate giornaliere riprende il giorno dopo senza rifare nulla. Ogni esecuzione ha un tetto di chiamate configurabile.

**Cosa resta bloccato.** Gli esiti negativi del fact-checking (ADR 0037) richiedono l'accordo tra due famiglie sull'interrogazione strutturata: con il solo Gemini non si pubblicano. Lo stesso vale per qualunque altro uso dell'ADR 0037 che chieda due famiglie.

## Alternative considerate
**Aspettare un secondo fornitore prima di generare il catalogo:** scartata, blocca il questionario, che è la parte più utile del prodotto. **Scrivere le domande a mano:** scartata dall'ADR 0030 per il rischio di bias di una sola persona. **Due modelli Gemini di taglia diversa come "due famiglie":** scartata, stessa famiglia e stesso addestramento; si possono usare per variare, non per verificare.

## Conseguenze
Il catalogo arriva presto, con un limite dichiarato. La seconda famiglia di modelli diventa un prerequisito del catalogo definitivo e della fase 3 (decisione aperta 3 del piano). La chiave di Gemini sta nei secret di GitHub e il job gira in GitHub Actions, che apre una pull request con il risultato: nessuna chiave nell'app web (0025).
