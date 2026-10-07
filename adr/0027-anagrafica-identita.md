# ADR 0027 — Anagrafica dei soggetti e risoluzione delle identità

**Stato:** Proposto
**Dettaglia:** ADR 0004 stadio 2

## Contesto
Collegare una dichiarazione a una persona sembra banale e non lo è. Camera e Senato usano identificativi propri e non conciliati tra loro: la stessa persona che è stata deputata e poi senatrice ha due identità diverse. Esistono omonimi, nomi riportati in forme diverse, soprannomi, cariche usate al posto del nome. I partiti si fondono, cambiano nome e simbolo, i gruppi parlamentari non coincidono con i partiti e i parlamentari cambiano gruppo in corso di legislatura.

Se questo strato sbaglia, sbagliano tutte le statistiche a valle, e l'errore è del tipo peggiore: attribuire a qualcuno parole o voti non suoi.

## Decisione
**Identità interna stabile.** Ogni persona ha un identificativo interno del progetto, indipendente da quelli delle fonti. Una tabella di corrispondenze collega l'identità interna agli identificativi esterni (Camera, Senato, eventuali altri), con il periodo di validità di ciascuno.

**Storia delle appartenenze.** Partito, gruppo parlamentare e carica sono relazioni con data di inizio e fine, non attributi della persona. Voti e dichiarazioni si attribuiscono al partito vigente alla data dell'evento (ADR 0023).

**Anagrafica dei partiti.** Anche i partiti hanno identità interna e storia: rinomina, fusione, scissione, con collegamenti di successione tra entità. L'interfaccia mostra la continuità quando esiste, e la interrompe quando non è definita.

**Alias controllati.** Per ogni persona si mantiene una lista di forme nominali accettate: nome completo, cognome, forme comuni nei media. La lista è dati versionati nel repository (ADR 0025), non generata automaticamente.

**Regola di attribuzione.** Un claim è attribuito a una persona solo se nel documento compare una forma nominale riconosciuta della lista. In caso di omonimia o ambiguità irrisolta il claim resta non attribuito e finisce in coda di ispezione: mai attribuzione probabilistica al soggetto più probabile.

**Portavoce e account di partito.** Le dichiarazioni rilasciate da profili o canali di partito sono attribuite al partito, non al leader, salvo firma esplicita.

**Controlli.** Test di contratto sulle fonti che verificano il conteggio dei parlamentari e la coerenza tra identificativi, e un controllo periodico che segnala persone con doppie identità o voti attribuiti fuori dal periodo di appartenenza.

## Alternative considerate
Usare gli identificativi della Camera come chiave primaria: si rompe per i senatori e per chi cambia ramo. Risoluzione automatica delle ambiguità tramite modello: scartata per il rischio di attribuzioni errate, che qui sono il danno peggiore.

## Conseguenze
Un lavoro iniziale di riconciliazione manuale limitato al perimetro dell'MVP, quindi contenuto. Una parte dei claim resterà non attribuita: è preferibile a un'attribuzione sbagliata e va mostrato nelle statistiche di copertura.
