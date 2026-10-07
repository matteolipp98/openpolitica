-- Programmi elettorali (ADR 0020, piano §4; issue #36). Corpus finito: i documenti depositati al
-- Ministero dell'Interno, salvati con impronta, e il loro testo diviso in paragrafi.
-- Il PDF non si conserva: l'indirizzo e l'impronta bastano a ritrovarlo e a riconoscerlo.

create table core.documento (
  id            uuid primary key default gen_random_uuid(),
  fonte         text not null,                -- es. 'interno-trasparenza'
  livello       char(1) not null check (livello in ('A', 'B', 'C')),  -- ADR 0003: A = fonte ufficiale
  url           text not null,
  data          date,                         -- data del documento o dell'elezione a cui si riferisce
  sha256        text not null unique check (sha256 ~ '^[0-9a-f]{64}$'),
  pagine        int not null check (pagine > 0),
  pagine_ocr    int not null default 0 check (pagine_ocr between 0 and pagine),  -- pagine lette con l'OCR
  registrato_il timestamptz not null default now()
);

create table core.documento_paragrafo (
  documento_id uuid not null references core.documento(id),
  n            int not null check (n > 0),    -- ordine nel documento
  pagina       int not null check (pagina > 0),
  testo        text not null check (length(testo) > 0),
  ocr          boolean not null,              -- letto con l'OCR: possibili errori di lettura
  primary key (documento_id, n)
);

-- Un programma per partito ed elezione. Le liste comuni (Azione e Italia Viva nel 2022) hanno
-- lo stesso documento per più partiti. I programmi comuni di coalizione, se depositati, avranno una tabella loro.
create table core.programma (
  id           uuid primary key default gen_random_uuid(),
  partito_id   uuid not null references core.partito(id),
  elezione     date not null,
  documento_id uuid not null references core.documento(id),
  unique (partito_id, elezione, documento_id)
);

-- Stesse regole delle altre tabelle pubblicate: append-only, scrive solo op_worker.
do $$
declare t text;
begin
  foreach t in array array['documento', 'documento_paragrafo', 'programma'] loop
    execute format(
      'create trigger %I before update or delete on core.%I for each row execute function core.append_only()',
      'append_only_' || t, t);
    execute format('alter table core.%I enable row level security', t);
    execute format('create policy worker_tutto on core.%I to op_worker using (true) with check (true)', t);
    execute format('grant select, insert on core.%I to op_worker', t);
  end loop;
end $$;
