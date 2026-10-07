-- Promesse estratte dai programmi (ADR 0020, piano §4; issue #37). Una promessa per misura, con la
-- citazione letterale controllata nel testo dei paragrafi da cui viene.
--
-- La promessa si lega al documento, non al programma: un documento comune a più partiti (Azione e
-- Italia Viva nel 2022) si legge una volta sola. I partiti si ritrovano da core.programma.
-- I cinque test (#38) e lo stato della promessa (ADR 0037) avranno colonne o tabelle loro.

-- Un lotto di paragrafi già mandato al modello. Con lo stesso modello e la stessa versione del prompt
-- un lotto non si richiede di nuovo: ogni esecuzione riprende dove si era fermata la precedente.
create table core.promessa_lotto (
  id              uuid primary key default gen_random_uuid(),
  documento_id    uuid not null references core.documento(id),
  paragrafo_da    int not null,
  paragrafo_a     int not null check (paragrafo_a >= paragrafo_da),
  modello_id      text not null references core.modello(id),      -- il modello chiesto, con versione
  prompt_versione text not null,                                  -- es. 'promesse/estrai.v1'
  input_sha256    text not null check (input_sha256 ~ '^[0-9a-f]{64}$'),  -- impronta del prompt completo
  run_modello_id  uuid not null references core.run_modello(id),  -- risposta completa, scarti compresi
  estratte        int not null check (estratte >= 0),             -- promesse tenute
  scartate        int not null check (scartate >= 0),             -- citazione non trovata nel testo
  registrato_il   timestamptz not null default now(),
  unique (documento_id, modello_id, prompt_versione, input_sha256),
  foreign key (documento_id, paragrafo_da) references core.documento_paragrafo(documento_id, n),
  foreign key (documento_id, paragrafo_a) references core.documento_paragrafo(documento_id, n)
);

create table core.promessa (
  id                  uuid primary key default gen_random_uuid(),
  documento_id        uuid not null references core.documento(id),
  lotto_id            uuid not null references core.promessa_lotto(id),
  paragrafo_da        int not null,                 -- paragrafi in cui si trova la citazione
  paragrafo_a         int not null check (paragrafo_a >= paragrafo_da),
  citazione           text not null check (length(citazione) > 0),  -- letterale, verificata nel testo
  misura              text not null check (length(misura) > 0),
  beneficiari         text,
  orizzonte           text,
  strumento_normativo text,
  livello_competenza  text check (livello_competenza in ('nazionale', 'regionale', 'ue', 'costituzionale')),
  costo_dichiarato    text,
  copertura_indicata  text,
  stato_revisione     text not null default 'non_rivista',
  registrato_il       timestamptz not null default now(),
  foreign key (documento_id, paragrafo_da) references core.documento_paragrafo(documento_id, n),
  foreign key (documento_id, paragrafo_a) references core.documento_paragrafo(documento_id, n)
);

create index promessa_documento on core.promessa (documento_id, paragrafo_da);

-- Stesse regole delle altre tabelle pubblicate: append-only, scrive solo op_worker.
do $$
declare t text;
begin
  foreach t in array array['promessa_lotto', 'promessa'] loop
    execute format(
      'create trigger %I before update or delete on core.%I for each row execute function core.append_only()',
      'append_only_' || t, t);
    execute format('alter table core.%I enable row level security', t);
    execute format('create policy worker_tutto on core.%I to op_worker using (true) with check (true)', t);
    execute format('grant select, insert on core.%I to op_worker', t);
  end loop;
end $$;
