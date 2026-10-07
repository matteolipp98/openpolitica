# ADR 0030 — Generazione automatica del catalogo e controlli sostitutivi della revisione umana

**Stato:** Proposto, modificato da ADR 0037 (la sezione "Nessun giudizio pubblicato senza revisore" è superata); ADR 0038 (con una sola famiglia di modelli il catalogo è provvisorio)
**Modifica:** ADR 0022, 0028

## Contesto
L'ADR 0022 affida a un panel pluralista la scrittura e la revisione degli enunciati, e l'ADR 0028 affida a revisori umani gli esiti negativi. Nella fase iniziale non esiste un panel e non c'è capacità di revisione: il progetto deve funzionare in modo automatico.

Il rischio è noto: chi scrive le domande decide il risultato. Formulazioni diverse della stessa questione spostano le affinità più di qualunque scelta di modello. Senza revisori serve un modo automatico per contenere questo effetto.

## Decisione

### Gli enunciati si derivano dai voti, non si scrivono
Il catalogo è generato dalle votazioni nominali, con questa procedura:

1. Si selezionano le votazioni finali su atti e le votazioni su emendamenti rilevanti dell'ultima legislatura.
2. Si tengono solo quelle **divisive**, cioè con una minoranza consistente su entrambi i fronti: una votazione quasi unanime non distingue nessuno.
3. Ogni votazione viene ricondotta a un tema della tassonomia.
4. Da ciascuna si genera un enunciato in linguaggio semplice, con un modello, a partire dall'oggetto dell'atto.
5. Si selezionano gli enunciati finali bilanciando il numero per tema.

L'enunciato nasce così già ancorato alla votazione da cui proviene: la mappatura voto-enunciato non è più un lavoro manuale né una scelta interpretativa.

### Controlli automatici che sostituiscono la rilettura umana
**Test di sensibilità alla formulazione.** Ogni enunciato viene riformulato in tre varianti da modelli di famiglie diverse. Si calcolano le posizioni con tutte le varianti: se le posizioni divergono oltre una soglia, l'enunciato è scartato perché la formulazione pesa più del contenuto.

**Test di polarità.** Ogni enunciato viene posto anche nella forma opposta. Le posizioni devono risultare speculari entro una tolleranza; altrimenti l'enunciato spinge in una direzione e viene scartato.

**Test di discriminazione.** Un enunciato su cui tutti i partiti risultano nella stessa posizione non aggiunge informazione e viene scartato.

**Test di equilibrio del catalogo.** Si simulano profili utente uniformi e casuali: se la distribuzione delle affinità favorisce sistematicamente un'area, il catalogo è sbilanciato per costruzione e va rigenerato.

Tutti i test girano nella suite di valutazione (ADR 0025) e bloccano la pubblicazione del catalogo.

### Nessun giudizio pubblicato senza revisore
> **Superata da ADR 0037.** Gli esiti dei claim quantitativi, le statistiche aggregate e lo stato delle promesse si pubblicano con le regole e le condizioni dell'ADR 0037; resta non pubblicato senza revisione solo l'esito "fuorviante per contesto". Testo originale:

Finché non c'è revisione umana, il fact-checking non pubblica verdetti. Pubblica **accostamenti**: la dichiarazione con la citazione e il link, il valore della serie ufficiale per lo stesso periodo con il link, senza etichetta di esito.

Le etichette "contraddetto" e "fuorviante per contesto" restano calcolate internamente e usate per le statistiche interne, ma non sono esposte al pubblico e non compaiono nelle pagine dei politici. Le percentuali aggregate dell'ADR 0019 restano non pubblicate finché non esiste capacità di revisione.

### Tracciabilità
Ogni enunciato registra la votazione di origine, il modello e il prompt che lo hanno generato, e l'esito di tutti i test. Il catalogo è versionato nel repository come gli altri dati metodologici.

## Alternative considerate
Enunciati scritti a mano da una persona sola: scartato, è il bias più probabile del progetto e il più facile da contestare. Attendere la formazione di un panel: scartato, bloccherebbe lo sviluppo a tempo indeterminato.

## Conseguenze
Il catalogo copre solo questioni arrivate al voto in Parlamento: restano fuori i temi su cui non si è votato, ed è un limite da dichiarare. La generazione automatica eredita il bias dei modelli nella formulazione, contenuto ma non eliminato dai test di sensibilità e polarità.

Questo ADR descrive una modalità iniziale. Quando esistono un panel e capacità di revisione, tornano a valere gli ADR 0022 e 0028: revisione degli enunciati, esiti espliciti di fact-checking e statistiche aggregate pubblicate.
