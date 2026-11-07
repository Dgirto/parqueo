CREATE TABLE IF NOT EXISTS tarifas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre      TEXT    NOT NULL,
    precio_hora REAL    NOT NULL,
    activa      INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS vehiculos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    placa        TEXT    NOT NULL UNIQUE,
    propietario  TEXT,
    tipo         TEXT    DEFAULT 'AUTO',
    created_at   TEXT    DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS tickets (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    placa         TEXT    NOT NULL,
    hora_entrada  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    hora_salida   TEXT,
    minutos       INTEGER,
    monto         REAL,
    tarifa_id     INTEGER DEFAULT 1,
    estado        TEXT    DEFAULT 'ACTIVO',
    FOREIGN KEY (tarifa_id) REFERENCES tarifas(id)
);

CREATE TABLE IF NOT EXISTS ajustes (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tickets_entrada ON tickets(hora_entrada);

CREATE INDEX IF NOT EXISTS idx_tickets_placa_activo
    ON tickets(placa, estado);

INSERT OR IGNORE INTO tarifas (id, nombre, precio_hora)
    VALUES (1, 'Tarifa General', 5.00);

INSERT OR IGNORE INTO ajustes (clave, valor) VALUES ('capacidad', '20');
