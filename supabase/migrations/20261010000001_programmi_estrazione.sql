-- Programmi: rilettura quando cambia l'estrazione del testo (issue #63, ADR 0005 append-only).
-- Ogni lettura di un documento ricorda la versione dell'estrazione con cui è stata fatta. Quando il codice
-- legge in modo diverso (per esempio l'OCR sulle pagine illeggibili, #62) il documento si rilegge: la nuova
-- lettura è una riga nuova di core.documento, con la stessa impronta e la versione nuova, e i suoi paragrafi.
-- Le letture vecchie restano; quella valida è la più recente (vista core.documento_attuale).

-- Le letture salvate fino a qui sono state fatte senza il controllo delle pagine illeggibili: versione 1.
alter table core.documento add column estrazione int not null default 1 check (estrazione > 0);
alter table core.documento alter column estrazione drop default;
alter table core.documento drop constraint documento_sha256_key;
alter table core.documento add constraint documento_sha256_estrazione_key unique (sha256, estrazione);

-- La lettura valida di ogni documento: la versione dell'estrazione più alta.
create view core.documento_attuale as
select distinct on (sha256) *
from core.documento
order by sha256, estrazione desc;

grant select on core.documento_attuale to op_worker;

-- Le promesse estratte dalla lettura valida. Quelle di una lettura vecchia restano nel database, ma non valgono:
-- la lettura nuova ha i suoi paragrafi e le sue promesse.
create view core.promessa_attuale as
select p.*
from core.promessa p
join core.documento_attuale d on d.id = p.documento_id;

grant select on core.promessa_attuale to op_worker;
