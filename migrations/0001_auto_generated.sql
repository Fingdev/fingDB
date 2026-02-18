-- upgrade

CREATE TABLE IF NOT EXISTS carreras (
    id INTEGER NOT NULL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at DATETIME NOT NULL
)

CREATE TABLE IF NOT EXISTS carrera_materias (
    id INTEGER NOT NULL PRIMARY KEY,
    carrera_id INTEGER NOT NULL REFERENCES carreras(id),
    materia_id INTEGER NOT NULL REFERENCES materias(id),
    tipo VARCHAR(20) NOT NULL
)

CREATE TABLE IF NOT EXISTS institutos (
    id INTEGER NOT NULL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at DATETIME NOT NULL
)

CREATE TABLE IF NOT EXISTS materias (
    id INTEGER NOT NULL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    periodo VARCHAR(11) NOT NULL,
    creditos INTEGER NOT NULL DEFAULT 0,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL,
    updated_at DATETIME,
    instituto_id INTEGER NOT NULL REFERENCES institutos(id)
)

CREATE TABLE IF NOT EXISTS materia_previas (
    materia_id INTEGER NOT NULL,
    previa_id INTEGER NOT NULL,
    tipo VARCHAR(9) NOT NULL,
    PRIMARY KEY (materia_id, previa_id, tipo),
    FOREIGN KEY(materia_id) REFERENCES materias(id) ON DELETE CASCADE,
    FOREIGN KEY(previa_id) REFERENCES materias(id) ON DELETE CASCADE
)

CREATE TABLE IF NOT EXISTS perfiles (
    id INTEGER NOT NULL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    carrera_id INTEGER NOT NULL REFERENCES carreras(id),
    created_at DATETIME NOT NULL
)

CREATE TABLE IF NOT EXISTS perfil_materias (
    id INTEGER NOT NULL PRIMARY KEY,
    perfil_id INTEGER NOT NULL REFERENCES perfiles(id),
    materia_id INTEGER NOT NULL REFERENCES materias(id),
    tipo VARCHAR(20) NOT NULL
)

-- rollback

DROP TABLE perfil_materias

DROP TABLE perfiles

DROP TABLE materia_previas

DROP TABLE materias

DROP TABLE institutos

DROP TABLE carrera_materias

DROP TABLE carreras
