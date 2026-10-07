-- Nelle votazioni segrete la Camera registra solo la partecipazione ("Ha votato"), non la direzione.
-- È un'espressione a sé: mai evidenza per le posizioni (ADR 0008).
alter type core.espressione add value if not exists 'votante_segreto';
