# ADR 0008 — Algoritmo di affinità deterministico e spiegabile

**Stato:** Proposto, modificato da ADR 0013 (LLM ammessi solo come intervistatore e spiegatore)

## Contesto
Il calcolo di quanto un politico sia vicino ai valori dell'utente influenza direttamente l'orientamento di voto. Se questo calcolo fosse opaco o generato da un LLM, sarebbe impossibile verificarne l'imparzialità e spiegarlo.

## Decisione
L'affinità è calcolata con un algoritmo deterministico e pubblico, senza LLM a runtime. Per ogni enunciato si confronta la posizione dell'utente con la posizione documentata del politico, pesata per l'importanza assegnata dall'utente al tema.

La posizione del politico su un enunciato è derivata dalle evidenze con una gerarchia fissa: voti nominali prima di atti presentati, atti prima di dichiarazioni. Se voti e dichiarazioni divergono, la divergenza non viene nascosta nella media: l'app mostra entrambe e segnala l'incoerenza.

Ogni risultato è scomponibile: l'utente vede per quale enunciato c'è concordanza o discordanza e con quali evidenze, fino alla citazione e alla fonte. Se le evidenze su un enunciato sono insufficienti, il politico risulta "posizione non documentata", mai stimata.

Gli LLM intervengono solo a monte, nello stadio 6 della pipeline, per proporre la mappatura tra evidenze ed enunciati, sempre soggetta a revisione umana prima della pubblicazione.

## Alternative considerate
Matching semantico generato da LLM in tempo reale: scartato perché non riproducibile e non auditabile. Posizionamento su assi ideologici (per esempio sinistra-destra, autoritario-libertario): scartato come unico output perché gli assi stessi sono contestati e comprimono le posizioni reali.

## Conseguenze
Il questionario ha un numero finito e curato di enunciati, da aggiornare periodicamente. La qualità dipende dalla copertura delle evidenze, che va mostrata all'utente. Il metodo è confrontabile con strumenti consolidati di orientamento al voto e può essere validato con quelle esperienze.
