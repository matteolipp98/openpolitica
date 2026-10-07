-- Conteggi per votazione e gruppo parlamentare (piano §3.5, decisione sullo spazio).
-- I voti individuali della legislatura sono ~10 milioni di righe: troppi per il database.
-- Si salvano invece i conteggi per gruppo, che bastano per le posizioni dei partiti, e il voto
-- individuale solo per le persone del perimetro e per i gruppi formati da più partiti.
create table core.votazione_gruppo (
  votazione_id  uuid not null references core.votazione(id),
  gruppo_id     uuid references core.gruppo_parlamentare(id),  -- null = parlamentari senza gruppo noto
  favorevoli    int not null default 0,
  contrari      int not null default 0,
  astenuti      int not null default 0,
  altri         int not null default 0,                        -- assenti, in missione, presidenza, voto segreto
  registrato_il timestamptz not null default now()
);
create unique index votazione_gruppo_unico
  on core.votazione_gruppo (votazione_id, coalesce(gruppo_id, '00000000-0000-0000-0000-000000000000'::uuid));

create trigger append_only_votazione_gruppo before update or delete on core.votazione_gruppo
  for each row execute function core.append_only();

alter table core.votazione_gruppo enable row level security;
create policy worker_tutto on core.votazione_gruppo to op_worker using (true) with check (true);
grant select, insert on core.votazione_gruppo to op_worker;

-- Registro delle migrazioni applicate (usato dallo script op_workers.comuni.migrazioni)
create table if not exists public.op_migrazioni (
  nome          text primary key,
  applicata_il  timestamptz not null default now()
);
