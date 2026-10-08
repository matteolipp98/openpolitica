-- Notizie, annunci e messaggi raccolti dalle fonti di content/fonti.yaml (ADR 0002, 0003, 0026; issue #41).
-- Un documento grezzo è il testo così come lo abbiamo letto, prima di qualunque modello: l'estrazione delle
-- dichiarazioni (#42) parte da qui.
--
-- Conservazione (ADR 0003): il testo dei giornali (livello C) si tiene al massimo 7 giorni, poi si cancella
-- e resta la data della cancellazione. Indirizzo, titolo, data e persone nominate restano. Se l'editore si
-- oppone al text and data mining, il testo non si salva affatto (tdm_riservato).

create table core.documento_grezzo (
  id                  uuid primary key default gen_random_uuid(),
  fonte               text not null,              -- id in content/fonti.yaml, oppure 'gdelt'
  livello             char(1) not null check (livello in ('A', 'B', 'C')),
  canale              text not null check (canale in ('rss', 'sito', 'telegram', 'gdelt')),
  url                 text not null unique,
  dominio             text not null,              -- per GDELT è la testata che ha pubblicato l'articolo
  titolo              text,
  pubblicato_il       timestamptz,
  sha256              text not null unique check (sha256 ~ '^[0-9a-f]{64}$'),  -- impronta del testo pulito
  testo               text,
  testo_scade_il      timestamptz,                -- quando il testo va cancellato; null = si conserva
  testo_cancellato_il timestamptz,
  tdm_riservato       boolean not null default false,
  soggetti            text[] not null default '{}',  -- slug delle persone del perimetro nominate nel testo
  sospetto            text,                       -- ADR 0026: perché il testo sembra rivolgersi ai modelli
  registrato_il       timestamptz not null default now(),
  check (livello <> 'C' or testo is null or testo_scade_il is not null),
  check (testo_cancellato_il is null or testo is null)
);
create index documento_grezzo_registrato on core.documento_grezzo (registrato_il);
create index documento_grezzo_soggetti on core.documento_grezzo using gin (soggetti);

-- Append-only, tranne la cancellazione del testo alla scadenza.
create or replace function core.documento_grezzo_solo_cancellazione() returns trigger
language plpgsql as $$
begin
  if tg_op = 'DELETE' or new.testo is not null or new.testo_cancellato_il is null
     or (new.id, new.fonte, new.livello, new.canale, new.url, new.dominio, new.titolo, new.pubblicato_il, new.sha256,
         new.testo_scade_il, new.tdm_riservato, new.soggetti, new.sospetto, new.registrato_il)
        is distinct from
        (old.id, old.fonte, old.livello, old.canale, old.url, old.dominio, old.titolo, old.pubblicato_il, old.sha256,
         old.testo_scade_il, old.tdm_riservato, old.soggetti, old.sospetto, old.registrato_il)
  then
    raise exception 'core.documento_grezzo: si può solo cancellare il testo, registrando quando' using errcode = 'P0001';
  end if;
  return new;
end $$;
create trigger solo_cancellazione before update or delete on core.documento_grezzo
  for each row execute function core.documento_grezzo_solo_cancellazione();

-- Un passaggio di raccolta per fonte: serve a vedere quando una fonte smette di funzionare (ADR 0002).
create table core.raccolta (
  id            uuid primary key default gen_random_uuid(),
  fonte         text not null,
  eseguita_il   timestamptz not null default now(),
  trovati       int not null check (trovati >= 0),   -- elementi visti nella fonte
  nuovi         int not null check (nuovi >= 0),     -- documenti salvati
  fuori         int not null default 0 check (fuori >= 0),  -- scartati perché non nominano nessuno del perimetro
  errore        text
);
create index raccolta_fonte on core.raccolta (fonte, eseguita_il desc);
create trigger append_only_raccolta before update or delete on core.raccolta
  for each row execute function core.append_only();

do $$
declare t text;
begin
  foreach t in array array['documento_grezzo', 'raccolta'] loop
    execute format('alter table core.%I enable row level security', t);
    execute format('create policy worker_tutto on core.%I to op_worker using (true) with check (true)', t);
    execute format('grant select, insert on core.%I to op_worker', t);
  end loop;
end $$;
grant update (testo, testo_cancellato_il) on core.documento_grezzo to op_worker;
