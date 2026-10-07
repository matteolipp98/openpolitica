# ADR 0009 — Nessun punteggio unico e UX contro l'effetto bolla

**Stato:** Proposto, modificato da ADR 0013 (graduatoria per affinità consentita con vincoli)

## Contesto
Classifiche e punteggi sintetici ("affidabilità 62%") sono attraenti e condivisibili, ma amplificano ogni bias residuo, sono i più attaccabili e riducono il giudizio a un numero. Un'app che conferma soltanto le convinzioni dell'utente rischia inoltre di rafforzare la polarizzazione.

## Decisione
Il livello fattuale non produce punteggi aggregati per politico né classifiche. Mostra profili descrittivi: claim verificati per esito con fonti, promesse con stato, coerenza tra dichiarazioni e voti, cambi di posizione nel tempo, sempre con il volume di evidenze e il livello di incertezza.

Il livello valoriale mostra l'affinità scomposta per tema, non una graduatoria unica, e include sempre le aree di disaccordo anche con i politici più affini.

Contro l'effetto bolla: per ogni tema l'app mostra le argomentazioni più forti a favore e contro, generate con il pattern steelman e revisionate; l'utente può vedere il profilo completo di qualunque politico, non solo dei più vicini; l'ordinamento predefinito delle liste è neutro (alfabetico o casuale), mai per affinità.

## Alternative considerate
Punteggio sintetico di attendibilità: scartato. Classifica di affinità stile quiz: consentita solo come vista secondaria scomposta, mai come risultato principale.

## Conseguenze
Prodotto meno virale ma più difendibile. Le schermate vanno testate con utenti per verificare che la complessità resti comprensibile.
