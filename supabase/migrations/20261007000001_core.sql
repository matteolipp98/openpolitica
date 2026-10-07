-- Schema della fase 0 (piano §3.2, ADR 0005, 0027, 0008, 0023).
-- Le tabelle con dati pubblicati sono append-only: una correzione è una nuova riga (ADR 0005).

create extension if not exists pgcrypto;
create schema if not exists core;

create or replace function core.append_only() returns trigger
language plpgsql as $$
begin
  raise exception 'La tabella %.% è append-only: inserire una nuova versione', tg_table_schema, tg_table_name
    using errcode = 'P0001';
end $$;

-- ---------- Anagrafica (ADR 0027) ----------
create table core.persona (
  id            uuid primary key default gen_random_uuid(),
  slug          text not null unique,
  nome          text not null,
  cognome       text not null,
  registrato_il timestamptz not null default now()
);

create table core.persona_id_esterno (
  persona_id    uuid not null references core.persona(id),
  fonte         text not null check (fonte in ('camera', 'senato', 'openpolis')),
  id_esterno    text not null,
  valido_dal    date not null,
  valido_al     date,
  registrato_il timestamptz not null default now(),
  primary key (fonte, id_esterno, valido_dal),
  check (valido_al is null or valido_al >= valido_dal)
);

create table core.partito (
  id            uuid primary key default gen_random_uuid(),
  slug          text not null unique,
  nome          text not null,
  registrato_il timestamptz not null default now()
);

create table core.partito_ruolo (
  partito_id    uuid not null references core.partito(id),
  ruolo         text not null check (ruolo in ('governo', 'opposizione')),
  valido_dal    date not null,
  valido_al     date,
  registrato_il timestamptz not null default now(),
  primary key (partito_id, valido_dal)
);

create table core.partito_successione (
  da_partito    uuid not null references core.partito(id),
  a_partito     uuid not null references core.partito(id),
  tipo          text not null check (tipo in ('rinomina', 'fusione', 'scissione')),
  data          date not null,
  primary key (da_partito, a_partito, data)
);

create table core.gruppo_parlamentare (
  id            uuid primary key default gen_random_uuid(),
  ramo          text not null check (ramo in ('camera', 'senato')),
  legislatura   smallint not null,
  id_esterno    text not null,
  registrato_il timestamptz not null default now(),
  unique (ramo, legislatura, id_esterno)
);

-- Nome e partiti di un gruppo cambiano nel tempo: lo stesso id_esterno può avere più periodi.
-- Più partiti nello stesso periodo = gruppo comune: i voti si attribuiscono per persona.
create table core.gruppo_periodo (
  gruppo_id     uuid not null references core.gruppo_parlamentare(id),
  nome          text not null,
  sigla         text,
  valido_dal    date not null,
  valido_al     date,
  registrato_il timestamptz not null default now(),
  primary key (gruppo_id, valido_dal)
);

create table core.gruppo_partito (
  gruppo_id     uuid not null references core.gruppo_parlamentare(id),
  partito_id    uuid not null references core.partito(id),
  valido_dal    date not null,
  valido_al     date,
  registrato_il timestamptz not null default now(),
  primary key (gruppo_id, partito_id, valido_dal)
);

-- Appartenenze come relazioni con periodo, non attributi (ADR 0027)
create table core.appartenenza (
  id            uuid primary key default gen_random_uuid(),
  persona_id    uuid not null references core.persona(id),
  tipo          text not null check (tipo in ('partito', 'gruppo', 'carica')),
  partito_id    uuid references core.partito(id),
  gruppo_id     uuid references core.gruppo_parlamentare(id),
  carica        text,
  valido_dal    date not null,
  valido_al     date,
  fonte_url     text,
  registrato_il timestamptz not null default now(),
  check (
    (tipo = 'partito' and partito_id is not null) or
    (tipo = 'gruppo'  and gruppo_id  is not null) or
    (tipo = 'carica'  and carica     is not null)
  )
);
create index on core.appartenenza (persona_id, tipo, valido_dal);

-- ---------- Voti ----------
create table core.votazione (
  id            uuid primary key default gen_random_uuid(),
  ramo          text not null check (ramo in ('camera', 'senato')),
  legislatura   smallint not null,
  id_esterno    text not null,              -- es. 'vs19_718_024' o '19-167-42'
  data          date not null,
  tipo          text,                       -- es. 'Emendamento', 'Finale atto Camera'
  titolo        text,                       -- spesso vuoto nella XIX alla Camera
  descrizione   text,                       -- es. 'DDL 3118 - VOTO FINALE'
  atto_ref      text,                       -- es. 'C.3118', 'S.1056'
  atto_titolo   text,
  finale        boolean not null,
  fiducia       boolean not null default false,
  segreta       boolean not null default false,
  favorevoli    int not null check (favorevoli >= 0),
  contrari      int not null check (contrari >= 0),
  astenuti      int not null check (astenuti >= 0),
  approvata     boolean,
  url           text not null,
  coerente      boolean not null default true, -- false se i voti individuali non tornano con i totali
  registrato_il timestamptz not null default now(),
  unique (ramo, legislatura, id_esterno)
);
create index on core.votazione (legislatura, data);

create type core.espressione as enum
  ('favorevole', 'contrario', 'astenuto', 'non_votante', 'assente', 'in_missione', 'presidente');

create table core.voto (
  votazione_id  uuid not null references core.votazione(id),
  persona_id    uuid not null references core.persona(id),
  espressione   core.espressione not null,
  gruppo_id     uuid references core.gruppo_parlamentare(id),
  registrato_il timestamptz not null default now(),
  primary key (votazione_id, persona_id)
);
create index on core.voto (persona_id);

-- Voti che non si riescono ad attribuire: mai attribuzione probabilistica (ADR 0027)
create table core.voto_non_attribuito (
  votazione_id  uuid not null references core.votazione(id),
  fonte         text not null,
  id_esterno    text not null,
  nominativo    text,
  motivo        text not null,
  registrato_il timestamptz not null default now()
);

-- ---------- Catalogo (ADR 0022, 0030) ----------
create table core.tema (
  id            text not null,
  versione      int not null,
  nome          text not null,
  primary key (id, versione)
);

create table core.enunciato (
  id                 text not null,
  versione           int  not null,
  catalogo_versione  text not null,
  testo              text not null,
  tema_id            text not null,
  livello_governo    text not null check (livello_governo in ('nazionale', 'regionale', 'ue')),
  stato              text not null check (stato in ('attivo', 'ritirato')),
  origine            jsonb not null,
  test               jsonb not null,
  registrato_il      timestamptz not null default now(),
  primary key (id, versione)
);

-- direzione +1: "favorevole alla votazione" = "d'accordo con l'enunciato"; -1 il contrario
create table core.ancoraggio (
  enunciato_id       text not null,
  enunciato_versione int  not null,
  votazione_id       uuid not null references core.votazione(id),
  direzione          smallint not null check (direzione in (-1, 1)),
  origine            text not null check (origine in ('generazione', 'manuale')),
  registrato_il      timestamptz not null default now(),
  primary key (enunciato_id, enunciato_versione, votazione_id),
  foreign key (enunciato_id, enunciato_versione) references core.enunciato(id, versione)
);

-- ---------- Posizioni (ADR 0008, 0023) ----------
create table core.posizione (
  id                 uuid primary key default gen_random_uuid(),
  soggetto_tipo      text not null check (soggetto_tipo in ('partito', 'persona', 'coalizione')),
  soggetto_id        uuid not null,
  enunciato_id       text not null,
  enunciato_versione int  not null,
  valore             smallint check (valore between -2 and 2),   -- null = non documentata
  stato              text not null check (stato in ('documentata', 'non_documentata', 'divergente')),
  confidenza         text check (confidenza in ('piena', 'ridotta')),
  origine            text not null check (origine in ('voto', 'dichiarazione')),
  evidenze           jsonb not null default '[]',
  calcolo_versione   text not null,
  valido_dal         date,
  registrato_il      timestamptz not null default now(),
  foreign key (enunciato_id, enunciato_versione) references core.enunciato(id, versione),
  check ((valore is null) = (stato = 'non_documentata')),
  check ((valore is null) = (confidenza is null))
);
create index on core.posizione (soggetto_tipo, soggetto_id, enunciato_id, registrato_il desc);

create view core.posizione_corrente as
select distinct on (soggetto_tipo, soggetto_id, enunciato_id) *
from core.posizione
order by soggetto_tipo, soggetto_id, enunciato_id, enunciato_versione desc, registrato_il desc, id;

-- ---------- Modelli e run (ADR 0016; già usati dal job di catalogo) ----------
create table core.modello (
  id            text primary key,           -- id con versione fissata, mai alias mobili
  fornitore     text not null,
  famiglia      text not null,
  parametri     jsonb not null default '{}',
  registrato_il timestamptz not null default now()
);

create table core.run_modello (
  id                    uuid primary key default gen_random_uuid(),
  stadio                text not null,
  modello_id            text not null references core.modello(id),
  prompt_id             text,
  prompt_versione       text,
  input_sha256          text not null,
  prompt_renderizzato   text,
  output                jsonb,
  parametri             jsonb,
  token_in              int,
  token_out             int,
  costo                 numeric,
  latenza_ms            int,
  esperimento_id        uuid,
  ripetizione           int,
  creato_il             timestamptz not null default now()
);

-- ---------- Rilasci, correzioni, segnalazioni (ADR 0012, 0037) ----------
create table core.rilascio (
  versione           text primary key,
  catalogo_versione  text not null,
  calcolo_versione   text not null,
  manifest           jsonb not null,
  storage_path       text not null,
  creato_il          timestamptz not null default now()
);

create table core.correzione (
  id                 uuid primary key default gen_random_uuid(),
  oggetto_tipo       text not null,
  oggetto_id         text not null,
  prima              jsonb not null,
  dopo               jsonb not null,
  motivazione        text not null,
  segnalazione_id    uuid,
  pubblicata_il      timestamptz not null default now()
);

create table core.segnalazione (
  id                 uuid primary key default gen_random_uuid(),
  oggetto_url        text not null check (length(oggetto_url) <= 500),
  testo              text not null check (length(testo) between 10 and 4000),
  contatto           text check (length(contatto) <= 200),
  stato              text not null default 'aperta' check (stato in ('aperta', 'accolta', 'respinta')),
  esito              text,
  creata_il          timestamptz not null default now()
);

-- ---------- Append-only ----------
do $$
declare t text;
begin
  foreach t in array array[
    'persona_id_esterno', 'partito_ruolo', 'gruppo_periodo', 'gruppo_partito', 'appartenenza',
    'votazione', 'voto', 'enunciato', 'ancoraggio', 'posizione', 'run_modello', 'rilascio', 'correzione'
  ] loop
    execute format(
      'create trigger %I before update or delete on core.%I for each row execute function core.append_only()',
      'append_only_' || t, t);
  end loop;
end $$;

-- ---------- Attribuzione alla data (ADR 0023, 0027) ----------
-- Partito di una persona alla data di un voto: il gruppo se corrisponde a un solo partito,
-- altrimenti (misto o gruppo comune) l'appartenenza di partito della persona. Mai una stima.
create or replace function core.partito_alla_data(p_persona uuid, p_gruppo uuid, p_data date)
returns uuid language sql stable as $$
  with da_gruppo as (
    select gp.partito_id from core.gruppo_partito gp
    where gp.gruppo_id = p_gruppo
      and p_data >= gp.valido_dal and (gp.valido_al is null or p_data <= gp.valido_al)
  ),
  da_persona as (
    select a.partito_id from core.appartenenza a
    where a.persona_id = p_persona and a.tipo = 'partito'
      and p_data >= a.valido_dal and (a.valido_al is null or p_data <= a.valido_al)
  )
  select case
    when (select count(*) from da_gruppo) = 1 then (select partito_id from da_gruppo)
    when (select count(*) from da_persona) = 1 then (select partito_id from da_persona)
    else null
  end
$$;
