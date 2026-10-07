# ADR 0016 — Laboratorio di misurazione del bias tra modelli e famiglie

**Stato:** Proposto, modificato da ADR 0038 (Gemini come unico fornitore iniziale)
**Estende:** ADR 0006

## Contesto
Oltre a produrre analisi per i cittadini, il progetto deve misurare come cambia l'output al variare del modello e della famiglia di modelli: se un modello tratta in modo diverso claim identici attribuiti a schieramenti diversi, se rifiuta più spesso su certi temi, se produce steelman più convincenti per una parte. La pipeline a stadi (ADR 0004) è un banco di prova ideale, perché ogni stadio ha input e output strutturati e confrontabili.

Il rischio è mescolare sperimentazione e produzione: un modello in prova non deve mai influenzare ciò che vedono gli utenti.

## Decisione
**Separazione tra laboratorio e produzione.** Il laboratorio esegue qualunque combinazione di modelli sugli stessi input. La produzione usa una configurazione "campione" versionata, promossa dal laboratorio solo se supera soglie di qualità e simmetria. Le configurazioni di produzione sono pubblicate.

**Registro dei modelli.** Ogni modello è censito con fornitore, famiglia, identificativo con versione fissata (mai alias che cambiano nel tempo), data, finestra di contesto, prezzo e parametri di inferenza. Le chiamate ai fornitori esterni passano da LiteLLM e quelle al motore di decisione dal servizio Laya (ADR 0032), quindi aggiungere o togliere un modello è una modifica di configurazione e non di codice. I checkpoint Laya, inclusi quelli adattati (ADR 0034), sono soggetti misurati come gli altri.

**Unità sperimentale.** Un esperimento è una matrice: stadio della pipeline × modello × variante di prompt × lingua del prompt × ripetizione. Ogni cella registra input, output strutturato, prompt renderizzato, parametri, latenza, token, costo e identificativo del run. Temperatura fissata e più ripetizioni per cella, perché gli output non sono deterministici nemmeno a temperatura zero.

**Dataset di valutazione.** Tre insiemi. Il golden set umano bilanciato (ADR 0006). Le coppie controfattuali: stesso claim, speaker di schieramenti diversi, e varianti con solo il nome del partito cambiato. Le persone sintetiche per l'assistente conversazionale (ADR 0013). Una parte del dataset è pubblica per trasparenza; una parte ruota ed è riservata, per evitare che finisca nei dati di addestramento dei modelli futuri e renda la misura inaffidabile.

**Metriche per modello, famiglia e stadio.** Delta controfattuale sugli esiti di verifica e classificazione. Asimmetria dei rifiuti per schieramento e per tema. Asimmetria di tono e lunghezza delle spiegazioni. Qualità comparata degli steelman a favore e contro. Posizionamento dei politici sugli enunciati rispetto ai voti reali. Accordo con il golden set umano. Sensibilità al prompt, cioè quanto l'esito cambia con riformulazioni equivalenti. Effetto della lingua, italiano contro inglese.

**Il problema del giudice.** Dove serve un giudizio automatico (tono, qualità dello steelman) si usano metriche deterministiche quando possibile, altrimenti una giuria di modelli di famiglie diverse calibrata su annotazioni umane. Un modello non giudica mai i propri output, per evitare la preferenza verso se stesso.

**Analisi statistica.** Intervalli di confidenza con bootstrap e modelli a effetti misti, con modello, famiglia, schieramento e tema come fattori. Un'asimmetria viene riportata solo se statisticamente distinguibile dal rumore delle ripetizioni.

**Pubblicazione.** Cruscotto pubblico con i risultati per modello e famiglia, metodologia, dataset pubblico e codice di valutazione. Ogni risultato riporta la versione esatta dei modelli e la data del run, perché i modelli cambiano.

## Alternative considerate
Misurare il bias solo sui benchmark esistenti: utile come riferimento ma insufficiente, perché non coprono il contesto politico italiano né i compiti specifici della pipeline. Usare in produzione il modello meno biased in assoluto: scartato, conta la combinazione di qualità e simmetria per stadio.

## Conseguenze
Costo di inferenza significativo per le matrici complete, mitigato con le Batch API dei fornitori dove disponibili e con campionamento stratificato. Il progetto produce un secondo asset pubblico, un benchmark di bias politico in italiano, con valore anche per la ricerca.

**Questione aperta.** Con i soli fornitori OpenAI e Anthropic il confronto tra famiglie è binario, e il segnale di disaccordo dell'ensemble è debole. Si possono confrontare generazioni e taglie dentro ciascuna famiglia, ma per una misura credibile servono almeno tre o quattro famiglie. LiteLLM permette di aggiungere Mistral, Google o modelli open-weight tramite fornitori di inferenza senza cambiare architettura: la decisione è rimandata ma raccomandata prima della pubblicazione dei risultati.
