# Fonti open data: cosa abbiamo verificato

Risultati della sonda `workers/op_workers/connettori/sonda_open_data.py`, eseguita in GitHub Actions (workflow "Verifica open data") il 2026-10-07. Il workflow gira ogni lunedì: se una fonte cambia forma, il rapporto lo mostra. È la base dei connettori della fase 0 (piano, §3.5) e dei loro test di contratto.

## Camera — `https://dati.camera.it/sparql`

Virtuoso, risponde in meno di un secondo. Ontologia OCD (`http://dati.camera.it/ocd/`).

**Attenzione: i dati sono duplicati.** Ogni votazione e ogni voto compaiono due volte (XIX legislatura: 39.471 righe per 19.673 votazioni distinte; in una votazione di esempio 794 righe per 397 voti). Ogni query del connettore deve usare `DISTINCT` o raggruppare per URI, e il controllo "somma dei voti = totali della votazione" va fatto sui distinti.

**Votazione** (`ocd:votazione`), URI `votazione.rdf/vs19_<seduta>_<numero>`:

| Proprietà | Esempio | Note |
|---|---|---|
| `ocd:rif_leg` | `legislatura.rdf/repubblica_19` | filtro per legislatura |
| `dc:date` | `20261001` | stringa AAAAMMGG |
| `dc:type` | `Emendamento`, `Finale atto Camera`, `Articolo`, `Ordine del Giorno`, `Mozione`, `Risoluzione`, `Altre`… | tipo di votazione |
| `ocd:votazioneFinale` | `1` / `0` | |
| `dc:title`, `rdfs:label` | `Votazione finale ` | poco informativo nella XIX |
| `dc:description` | `DDL 3118 - VOTO FINALE`, `EM 1.11` | contiene il numero dell'atto |
| `ocd:rif_attoCamera` | `attocamera.rdf/ac19_3118` | presente su quasi tutti gli emendamenti e sull'89% delle votazioni finali (800 righe su 902); mancante nelle più recenti, dove il numero dell'atto si ricava da `dc:description` |
| `ocd:favorevoli`, `ocd:contrari`, `ocd:astenuti`, `ocd:presenti`, `ocd:votanti`, `ocd:maggioranza` | numeri | |
| `ocd:approvato` | `1` / `0` | |
| `ocd:richiestaFiducia`, `ocd:votazioneSegreta` | `1` / `0` | da escludere dal catalogo (ADR 0030) |
| `dc:relation` | link alla scheda della votazione su camera.it | da mostrare come fonte |

Votazioni XIX legislatura (al 2026-10-07): 19.673 distinte, l'ultima del 1° ottobre 2026. Ripartizione per tipo in righe, quindi con i duplicati (i distinti sono circa la metà): emendamenti 16.713, ordini del giorno 13.881, articoli 4.340, mozioni 2.504, altre 2.338, risoluzioni 1.514, finali 1.146 (902 con `votazioneFinale = 1`). Il conteggio esatto per tipo va rifatto con `COUNT(DISTINCT ?v)` nel test di contratto.

**Voto** (`ocd:voto`):

| Proprietà | Esempio |
|---|---|
| `ocd:rif_votazione` | `votazione.rdf/vs19_718_011` |
| `ocd:rif_deputato` | `deputato.rdf/d302103_19` |
| `ocd:rif_gruppoParlamentare` | `gruppoParlamentare.rdf/gr4133` |
| `ocd:siglaGruppo` | `FDI` |
| `dc:type` | `Favorevole`, `Contrario`, `Astensione`, `Non ha votato` |
| `dc:description` | per `Non ha votato`: `Non ha partecipato`, `In missione`, `Presidente di turno` |

Corrispondenza con `core.espressione`: Favorevole → `favorevole`, Contrario → `contrario`, Astensione → `astenuto`, Non ha votato + Non ha partecipato → `non_votante`, + In missione → `in_missione`, + Presidente di turno → `presidente`.

**Atto** (`ocd:atto`, `attocamera.rdf/ac19_<numero>`): `rdfs:label` con il titolo completo (es. "Conversione in legge, con modificazioni, del decreto-legge…"), `ocd:iniziativa` (Governo/Parlamentare), `ocd:rif_natura`. Il titolo dell'atto è il testo da cui il job di catalogo genera l'enunciato (ADR 0030).

**Deputato** (`ocd:deputato`, `deputato.rdf/d<persona>_<legislatura>`): il numero `<persona>` è stabile tra le legislature e va in `persona_id_esterno` (fonte `camera`). `foaf:firstName`, `foaf:surname` in maiuscolo, `ocd:rif_mandatoCamera`, `ocd:aderisce` → adesione a un gruppo con `ocd:rif_gruppoParlamentare`, `ocd:startDate`, `ocd:endDate`, `rdfs:label` tipo `MISTO (18.10.2022-27.10.2022)`.

**Gruppi della XIX** (`ocd:gruppoParlamentare` con `ocd:rif_leg`): sono in `content/gruppi.yaml`, stato `verificato`. Il gruppo `gr4135` ha cambiato nome il 20.11.2023 (da "Azione - Italia Viva - Renew Europe" ad "Azione-Popolari europeisti riformatori-Renew Europe"), lo stesso giorno in cui nasce `gr4211` "Italia Viva-Casa riformista". La storia dei nomi è in `ocd:denominazione`.

## Senato — `https://dati.senato.it/sparql`

Virtuoso, più lento (1-8 secondi), ontologia OSR (`http://dati.senato.it/osr/`) con alcune classi OCD della Camera.

**Limiti del server:** rifiuta `VALUES` (HTTP 400): usare `FILTER(?x IN (...))`. Le query di profilo con sottoquery e `GROUP BY` possono dare 400 o 500: preferire query semplici su risorse note.

**Votazione** (`osr:Votazione`), URI `votazione/<leg>-<seduta>-<numero>`; 8.303 nella XIX:

| Proprietà | Note |
|---|---|
| `osr:legislatura` | `19` (anche sulla seduta) |
| `osr:seduta` → `osr:SedutaAssemblea` | `osr:dataSeduta` (data ISO), `osr:numeroSeduta` |
| `osr:oggetto` → `osr:OggettoTrattazione` | `osr:relativoA` → `ddl/<idFase>` |
| `rdfs:label` | es. `Votazione finale` |
| `osr:favorevoli`, `osr:contrari`, `osr:astenuti`, `osr:presenti`, `osr:votanti`, `osr:maggioranza`, `osr:congedoMissione` | numeri |
| `osr:esito`, `osr:tipoVotazione`, `osr:numero`, `osr:numeroLegale` | |
| `osr:favorevole`, `osr:contrario`, `osr:astenuto`, `osr:presenteNonVotante`, `osr:inCongedoMissione`, `osr:presidente`, `osr:votante`, `osr:presente` | **un arco per senatore**: il voto individuale è una proprietà della votazione, non una risorsa a sé |

I voti individuali non risultano duplicati (86 archi `osr:favorevole` per 86 favorevoli dichiarati).

**Disegno di legge** (`osr:Ddl`, `ddl/<idFase>`): `osr:titolo`, `osr:titoloBreve` (es. "d-l 5/2024 - Infrastrutture presidenza G7"), `osr:natura`, `osr:statoDdl`, `osr:numeroLegge`, `osr:fase` (es. `S.1056`), `osr:descrIniziativa`.

**Senatore** (`osr:Senatore`, `senatore/<id>`): `foaf:firstName`, `foaf:lastName`, mandati `ocd:mandatoSenato` (`mandato/S_<leg>_<id>_<n>`, con `osr:inizio`, `osr:fine`, `osr:legislatura`, `osr:tipoMandato`), adesioni `ocd:aderisce` → `ocd:adesioneGruppo` con `osr:gruppo`, `osr:inizio`, `osr:fine`, `osr:carica`, `osr:legislatura`. Le adesioni compaiono duplicate.

**Gruppi** (`gruppo/<id>`): un solo identificativo per tutta la storia del gruppo; i nomi sono in `osr:denominazione` → `osr:Denominazione` con `osr:titolo`, `osr:titoloBreve`, `osr:inizio`, `osr:fine`. Esempio: `gruppo/49` è "Partito Democratico - Italia Democratica e Progressista" dal 13.10.2022; `gruppo/33` è la Lega. I gruppi della XIX sono in `content/gruppi.yaml`, stato `verificato`. Da notare: `gruppo/91` nasce come "Azione-ItaliaViva-RenewEurope", diventa "Italia Viva - Il Centro - Renew Europe" il 9.11.2023 (quando Calenda passa al Misto, `gruppo/9`) e "Italia Viva - Casa Riformista" il 15.6.2026; `gruppo/92` riunisce Noi Moderati con UDC, Coraggio Italia, Italia al Centro e MAIE.

Alla Camera invece l'etichetta del gruppo riporta il nome **attuale** con la data di costituzione: per esempio "ITALIA VIVA-CASA RIFORMISTA (20.11.2023" non significa che si chiamasse così nel 2023. Per il nome alla data di un voto va usata la storia in `ocd:denominazione`.

## Componenti politiche del gruppo misto

Servono per dare un partito a chi sta nel misto (issue #78; regola e corrispondenze in `content/componenti-misto.yaml`).

- **Camera**: classe `ocd:componenteGruppoMisto` (`componenteGruppoMisto.rdf/cgm<id>`), con `ocd:rif_leg`, `dcterms:alternative` (sigla), `ocd:startDate`/`ocd:endDate` e `ocd:siComponeDi` → nodo con `ocd:rif_deputato`, `ocd:startDate`, `ocd:endDate`. Nella XIX sono 5: minoranze linguistiche (cgm4137), AVS (cgm4138, solo 19-27.10.2022), +Europa (cgm4139), Noi Moderati-MAIE (cgm4148, solo 19-27.10.2022), Futuro Nazionale Vannacci (cgm4271, dal 27.5.2026). Il nodo `ocd:componente` sulle adesioni al misto è vuoto: non serve.
- **Senato**: dati.senato.it **non** pubblica le componenti (le adesioni hanno solo `osr:gruppo`, `osr:carica`, `osr:inizio`, `osr:fine`; nessuna classe dedicata). La componente è scritta nella scheda del senatore su senato.it ("Misto (Alleanza Verdi e Sinistra)"), che però risponde 403/202 vuoto alle letture automatiche: le adesioni sono scritte a mano nel file, con la scheda come fonte.

## Leader del perimetro

| Persona | Ramo | Identificativo | Gruppo nella XIX |
|---|---|---|---|
| Giorgia Meloni | Camera | 302103 | FDI |
| Elly Schlein (Elena Ethel) | Camera | 308930 | PD-IDP |
| Giuseppe Conte | Camera | 307926 | M5S |
| Antonio Tajani | Camera | 308838 | FI-PPE |
| Angelo Bonelli | Camera | 302080 | Misto fino al 27.10.2022, poi AVS |
| Nicola Fratoianni | Camera | 305880 | Misto fino al 27.10.2022, poi AVS |
| Maurizio (Enzo) Lupi | Camera | 300447 | Misto fino al 27.10.2022, poi Noi Moderati |
| Matteo Salvini | Senato | 25407 | gruppo/33 (LSP-PSd'Az) |
| Matteo Renzi | Senato | 30742 | gruppo/91 (Az-IV-RE, poi IV-C-RE, poi IV-CR) |
| Carlo Calenda | Senato | 30110 | gruppo/91 fino all'8.11.2023, poi Misto (gruppo/9) |

Al Senato ci sono omonimi tra i cognomi del perimetro (tre Conte, due Meloni, una Tajani): l'abbinamento usa nome e cognome e il mandato nella XIX, mai il solo cognome (ADR 0027).

## Altre fonti

| Fonte | Esito | Note |
|---|---|---|
| Eurostat (API di diffusione JSON) | OK, < 1 s | pronta per la fase 3 |
| Normattiva, Gazzetta Ufficiale | OK | pagine HTML; nessuna API verificata |
| Programmi elettorali (dait.interno.gov.it/elezioni/trasparenza) | OK | da esplorare in fase 1 |
| Wayback Machine CDX | OK, lenta (25-40 s) | per i programmi non più online |
| Sito Openpolis | OK | l'host `service.openpolis.it` non esiste: le API di Openpolis vanno cercate altrove, ma Camera e Senato bastano per la fase 0 |
| ISTAT SDMX (esploradati.istat.it) | **timeout a 180 s** sull'elenco completo dei dataflow | in fase 3 interrogare direttamente i dataflow del catalogo indicatori, non l'elenco; il vecchio endpoint `sdmx.istat.it` risponde con un redirect |
| GDELT DOC API | **HTTP 429** anche dopo due attese | limiti stretti dagli IP condivisi di GitHub; in fase 2 serve un ritmo di chiamate basso dal worker su Render |
