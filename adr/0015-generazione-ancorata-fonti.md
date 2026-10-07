# ADR 0015 — Generazione ancorata alle fonti e validazione delle citazioni

**Stato:** Proposto

## Contesto
Spiegatore, intervistatore e schede di fact-checking producono testo che l'utente leggerà come affermazione dell'app. Le citazioni generate da un LLM possono essere inventate, attribuite alla fonte sbagliata o non supportare davvero la frase.

## Decisione
Ogni testo generato che contiene fatti o numeri segue quattro vincoli.

**Pacchetto di evidenze chiuso.** Il modello riceve solo evidenze con identificativo e non ha accesso ad altre fonti in quella chiamata.

**Numeri come segnaposto.** Il modello scrive riferimenti come `{{dato:ID}}` invece dei valori; il sistema li sostituisce con i valori calcolati. Un numero letterale scritto dal modello invalida la frase.

**Citazione per frase.** Ogni frase fattuale deve riportare almeno un identificativo di evidenza.

**Validazione post-generazione.** Un validatore deterministico controlla che gli identificativi esistano e che le citazioni testuali compaiano nella fonte. Un modello di famiglia diversa verifica che l'evidenza supporti la frase. Le frasi che falliscono vengono rigenerate una volta, poi rimosse. Se la spiegazione perde parti essenziali si usa un testo a template.

Le spiegazioni di politici diversi vengono generate con la stessa struttura, lo stesso limite di lunghezza e lo stesso numero massimo di evidenze per sezione, per evitare asimmetrie di tono o di dettaglio.

## Alternative considerate
Citazioni affidate al solo prompt: scartato, perché è la causa principale delle citazioni inventate. Solo testi a template: più sicuro ma rigido; resta come fallback.

## Conseguenze
Latenza aggiuntiva nelle risposte dell'assistente, mitigata da streaming delle parti già validate e da caching delle spiegazioni per profili di affinità simili. Tasso di frasi rimosse e tasso di fallback diventano metriche di qualità monitorate e pubblicate.
