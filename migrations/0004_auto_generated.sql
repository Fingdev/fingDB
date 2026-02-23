-- upgrade

ALTER TABLE materias ADD COLUMN min_creditos INTEGER 

-- rollback

ALTER TABLE materias DROP COLUMN min_creditos
