-- Tema di ogni promessa (issue #75): uno dei 6 temi di content/temi.yaml, oppure 'altro'.
-- Serve alla home (blocco "Di cosa parla il programma"). Il tema sta in una tabella sua: core.promessa non cambia.
--
-- Append-only (ADR 0005): un tema nuovo per la stessa promessa (prompt nuovo, revisione) è una riga nuova;
-- vale la più recente (vista core.promessa_tema_attuale).

-- Un lotto di promesse già mandato al modello, con la risposta completa in core.run_modello.
create table core.promessa_tema_lotto (
  id              uuid primary key default gen_random_uuid(),
  modello_id      text not null references core.modello(id),      -- il modello chiesto, con versione
  prompt_versione text not null,                                  -- es. 'promesse/tema.v1'
  input_sha256    text not null check (input_sha256 ~ '^[0-9a-f]{64}$'),  -- impronta del prompt completo
  run_modello_id  uuid not null references core.run_modello(id),
  classificate    int not null check (classificate >= 0),         -- promesse con un tema valido
  scartate        int not null check (scartate >= 0),             -- risposte senza promessa o tema valido
  registrato_il   timestamptz not null default now(),
  unique (modello_id, prompt_versione, input_sha256)
);

create table core.promessa_tema (
  id            uuid primary key default gen_random_uuid(),
  promessa_id   uuid not null references core.promessa(id),
  lotto_id      uuid not null references core.promessa_tema_lotto(id),
  tema          text not null
                check (tema in ('economia', 'welfare', 'diritti', 'ambiente', 'istituzioni', 'esteri', 'altro')),
  registrato_il timestamptz not null default now(),
  unique (promessa_id, lotto_id)
);

create index promessa_tema_promessa on core.promessa_tema (promessa_id, registrato_il desc);

-- Il tema valido di ogni promessa: l'ultimo registrato.
create view core.promessa_tema_attuale as
select distinct on (promessa_id) *
from core.promessa_tema
order by promessa_id, registrato_il desc, id;

grant select on core.promessa_tema_attuale to op_worker;

-- Stesse regole delle altre tabelle pubblicate: append-only, scrive solo op_worker.
do $$
declare t text;
begin
  foreach t in array array['promessa_tema_lotto', 'promessa_tema'] loop
    execute format(
      'create trigger %I before update or delete on core.%I for each row execute function core.append_only()',
      'append_only_' || t, t);
    execute format('alter table core.%I enable row level security', t);
    execute format('create policy worker_tutto on core.%I to op_worker using (true) with check (true)', t);
    execute format('grant select, insert on core.%I to op_worker', t);
  end loop;
end $$;
