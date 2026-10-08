-- Correzioni dell'atto di una votazione (#74). core.votazione è append-only (ADR 0005): quando la scelta
-- dell'atto cambia (al Senato una votazione finale può avere più disegni di legge e conta quello approvato)
-- la correzione è una riga nuova qui, con la data. Vale l'ultima; senza correzioni vale core.votazione.
create table core.votazione_atto (
  votazione_id  uuid not null references core.votazione(id),
  atto_ref      text,
  atto_titolo   text,               -- vuoto: il titolo del testo votato non è nei dati (testo unificato)
  registrato_il timestamptz not null default now(),
  primary key (votazione_id, registrato_il)
);

create trigger append_only_votazione_atto before update or delete on core.votazione_atto
  for each row execute function core.append_only();
alter table core.votazione_atto enable row level security;
create policy worker_tutto on core.votazione_atto to op_worker using (true) with check (true);
grant select, insert on core.votazione_atto to op_worker;

-- Atto e titolo in vigore per ogni votazione: da leggere al posto delle colonne di core.votazione.
create view core.votazione_atto_corrente as
select v.id as votazione_id, v.ramo, v.legislatura, v.id_esterno,
       case when c.votazione_id is null then v.atto_ref else c.atto_ref end as atto_ref,
       case when c.votazione_id is null then v.atto_titolo else c.atto_titolo end as atto_titolo
from core.votazione v
left join lateral (
  select a.votazione_id, a.atto_ref, a.atto_titolo from core.votazione_atto a
  where a.votazione_id = v.id order by a.registrato_il desc limit 1
) c on true;
grant select on core.votazione_atto_corrente to op_worker;
