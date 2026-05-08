-- =============================================================================
-- HematologIA — esquema de base de datos
-- =============================================================================
-- Este archivo es la fuente de verdad del esquema. `scripts/init_db.py` lo lee
-- y lo ejecuta sobre `data/hematologia.db`.
--
-- Convenciones (ver CLAUDE.md sección 5):
--   * Nombres de tablas y columnas en español (preserva el contexto del dominio)
--   * Nombres de identificadores en código en inglés
--
-- En Fase 1 sólo necesitamos `operarios` para soportar el login. Las tablas de
-- pacientes, estudios y capturas se agregarán incrementalmente cuando se
-- construyan las ventanas correspondientes.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- Tabla: operarios
-- -----------------------------------------------------------------------------
-- Representa al personal del laboratorio que usa la aplicación.
-- Cada operario tiene un único rol ('jefe' o 'personal') que determina los
-- permisos de la sesión.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS operarios (
    -- PK autoincremental. SQLite usa INTEGER PRIMARY KEY como alias de ROWID.
    id_operario       INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Datos personales. Convención hispana: nombre + apellido paterno + apellido materno.
    -- `apellido_materno` es nullable porque hay extranjeros que no tienen segundo apellido.
    nombre            TEXT    NOT NULL,
    apellido_paterno  TEXT    NOT NULL,
    apellido_materno  TEXT,

    -- Credenciales de acceso.
    -- `usuario` es UNIQUE: garantiza que no haya colisiones de login.
    -- `password_hash` almacena el hash bcrypt completo (formato `$2b$<cost>$<salt+hash>`),
    -- nunca el password en plano. Se compara con `bcrypt.checkpw`, nunca con `=`.
    usuario           TEXT    NOT NULL UNIQUE,
    password_hash     TEXT    NOT NULL,

    -- Rol del operario. CHECK garantiza que sólo sean valores válidos a nivel DB,
    -- así un bug en código no puede insertar un rol arbitrario.
    rol               TEXT    NOT NULL CHECK(rol IN ('jefe', 'personal')),

    -- Soft-delete: en lugar de eliminar operarios físicamente (lo que rompería
    -- referencias futuras desde estudios/capturas), los marcamos como inactivos.
    -- INTEGER 0/1 porque SQLite no tiene tipo BOOLEAN nativo.
    activo            INTEGER NOT NULL DEFAULT 1,

    -- Auditoría temporal. SQLite almacena TIMESTAMP como TEXT (ISO 8601) por defecto.
    -- `fecha_creacion` se setea automáticamente al insertar.
    -- `ultimo_acceso` se actualiza desde el código en cada login exitoso.
    fecha_creacion    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ultimo_acceso     TIMESTAMP
);

-- Índice sobre `usuario` para acelerar los lookups del login.
-- Es redundante con el UNIQUE (que ya crea un índice implícito), pero lo dejamos
-- explícito para que sea evidente la intención de optimización del query del login.
CREATE INDEX IF NOT EXISTS idx_operarios_usuario ON operarios(usuario);
