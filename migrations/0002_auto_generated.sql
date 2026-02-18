-- upgrade

CREATE TABLE IF NOT EXISTS materia_previas (
    materia_id INTEGER NOT NULL PRIMARY KEY REFERENCES materias(id),
    previa_id INTEGER NOT NULL PRIMARY KEY REFERENCES materias(id),
    tipo VARCHAR(9) NOT NULL PRIMARY KEY
)

-- rollback

DROP TABLE materia_previas
