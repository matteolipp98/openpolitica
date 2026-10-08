-- Partito alla data (issue #78): una persona può avere più righe di appartenenza allo stesso partito che si
-- sovrappongono (per esempio un leader del perimetro che è anche in una componente del misto). Conta il
-- numero di partiti diversi, non di righe: due righe dello stesso partito non devono annullare l'attribuzione.
create or replace function core.partito_alla_data(p_persona uuid, p_gruppo uuid, p_data date)
returns uuid language sql stable as $$
  with da_gruppo as (
    select distinct gp.partito_id from core.gruppo_partito gp
    where gp.gruppo_id = p_gruppo
      and p_data >= gp.valido_dal and (gp.valido_al is null or p_data <= gp.valido_al)
  ),
  da_persona as (
    select distinct a.partito_id from core.appartenenza a
    where a.persona_id = p_persona and a.tipo = 'partito'
      and p_data >= a.valido_dal and (a.valido_al is null or p_data <= a.valido_al)
  )
  select case
    when (select count(*) from da_gruppo) = 1 then (select partito_id from da_gruppo)
    when (select count(*) from da_persona) = 1 then (select partito_id from da_persona)
    else null
  end
$$;
