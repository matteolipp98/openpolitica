-- Segnalazioni dal sito (ADR 0012, 0026; issue #26). Il sito è statico: chiama questa funzione con la chiave
-- pubblica (ruolo anon) tramite l'API di Supabase. L'indirizzo di chi scrive non si salva: solo un codice
-- ricavato dall'indirizzo e dalla data, che cambia ogni giorno, per bloccare chi manda troppe segnalazioni.

alter table core.segnalazione add column if not exists origine text;
create index if not exists segnalazione_origine on core.segnalazione (origine, creata_il);

create or replace function public.segnala(
  p_url text, p_testo text, p_contatto text default null, p_trappola text default null
) returns json language plpgsql security definer set search_path = core, pg_temp as $$
declare
  intestazioni json := nullif(current_setting('request.headers', true), '')::json;
  indirizzo text := coalesce(trim(split_part(intestazioni ->> 'x-forwarded-for', ',', 1)), '');
  codice text := encode(sha256(convert_to(indirizzo || '|' || current_date::text, 'UTF8')), 'hex');
begin
  -- Campo trappola: le persone non lo vedono, i programmi automatici lo riempiono. Finto successo.
  if coalesce(p_trappola, '') <> '' then
    return json_build_object('ok', true);
  end if;
  if length(coalesce(p_testo, '')) < 10 then
    raise exception 'testo troppo corto' using errcode = '22023';
  end if;
  if (select count(*) from core.segnalazione where origine = codice and creata_il > now() - interval '1 hour') >= 5 then
    raise exception 'troppe segnalazioni, riprova tra un''ora' using errcode = '54000';
  end if;
  if (select count(*) from core.segnalazione where creata_il > now() - interval '1 day') >= 500 then
    raise exception 'troppe segnalazioni oggi' using errcode = '54000';
  end if;
  insert into core.segnalazione (oggetto_url, testo, contatto, origine)
  values (left(p_url, 500), left(p_testo, 4000), nullif(left(p_contatto, 200), ''), codice);
  return json_build_object('ok', true);
end
$$;

revoke all on function public.segnala(text, text, text, text) from public;
do $$
begin
  if exists (select from pg_roles where rolname = 'anon') then
    grant execute on function public.segnala(text, text, text, text) to anon;
  end if;
end $$;
