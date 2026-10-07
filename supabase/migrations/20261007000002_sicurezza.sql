-- Sicurezza (ADR 0026). Il sito pubblico non legge il database: legge il bundle di rilascio (piano §3.9).
-- I worker usano il ruolo op_worker, non la service key; il pubblico può solo inviare segnalazioni.

do $$
begin
  if not exists (select from pg_roles where rolname = 'op_worker') then
    create role op_worker nologin;
  end if;
end $$;

grant usage on schema core to op_worker;
grant select, insert on all tables in schema core to op_worker;
grant select on core.posizione_corrente to op_worker;
grant execute on function core.partito_alla_data(uuid, uuid, date) to op_worker;
-- Le uniche righe modificabili dai worker sono quelle non pubblicate
grant update on core.persona, core.partito, core.gruppo_parlamentare, core.segnalazione to op_worker;

do $$
declare t text;
begin
  for t in select tablename from pg_tables where schemaname = 'core' loop
    execute format('alter table core.%I enable row level security', t);
    execute format('create policy worker_tutto on core.%I to op_worker using (true) with check (true)', t);
  end loop;
end $$;

-- Segnalazioni dal sito: solo tramite questa funzione, con i limiti di lunghezza della tabella.
create or replace function core.segnala(p_url text, p_testo text, p_contatto text default null)
returns uuid language sql security definer set search_path = core, pg_temp as $$
  insert into core.segnalazione (oggetto_url, testo, contatto) values (p_url, p_testo, p_contatto) returning id
$$;
revoke all on function core.segnala(text, text, text) from public;

do $$
begin
  if exists (select from pg_roles where rolname = 'anon') then
    grant usage on schema core to anon;
    grant execute on function core.segnala(text, text, text) to anon;
  end if;
end $$;
