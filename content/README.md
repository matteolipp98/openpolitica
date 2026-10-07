# Contenuto metodologico

Dati versionati che decidono come funziona il sito (ADR 0025). Ogni modifica passa da una pull request ed è validata in CI con `pnpm content:check`.

| File | Cosa contiene | ADR |
|---|---|---|
| `temi.yaml` | I temi delle domande | 0022, 0035 |
| `scala.yaml` | I cinque livelli di posizione, uguali ovunque | 0035 |
| `parametri.yaml` | Soglie di calcolo e di presentazione | 0019, 0023, 0030, 0037 |
| `letture.yaml` | Le frasi "In breve" e le frasi per soggetto | 0037 |
| `governance.yaml` | Revisione umana attiva o no, modalità campagna | 0021, 0028, 0037 |
| `perimetro.yaml` | Chi seguiamo e perché | 0002 |
| `partiti.yaml` | Partiti, ruolo (governo/opposizione), coalizioni | 0021, 0027 |
| `gruppi.yaml` | Gruppi parlamentari e partito corrispondente | 0027 |
| `alias/<slug>.yaml` | Nomi con cui una persona compare nei testi, cariche, identificativi esterni | 0027 |
| `schema/` | JSON Schema generati da `packages/schema` (`pnpm content:schema`), non si modificano a mano | 0025 |

## Regole

- **Mai inventare.** Un fatto non ancora confermato su una fonte si marca `da_verificare: true` (o `stato: da_verificare`). `pnpm content:check` li elenca.
- **Il lettore è l'italiano medio.** Nomi e descrizioni visibili nel sito usano parole di tutti i giorni (ADR 0036).
- Gli identificativi di Camera e Senato e i gruppi si compilano dai risultati della verifica open data (`workers/op_workers/connettori/sonda_open_data.py`), non a mano.
