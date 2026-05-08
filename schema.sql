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
-- Estado: Fase 1 — incluye operarios (login) + tablas necesarias para que el
-- dashboard del Personal pueda mostrar stats reales (capturas/análisis/reportes
-- por día). Las ventanas que llenan estas tablas se construirán en sprints
-- posteriores.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- Tabla: operarios
-- -----------------------------------------------------------------------------
-- Personal del laboratorio que usa la aplicación.
-- Cada operario tiene un único rol ('jefe' o 'personal') que determina los
-- permisos de la sesión.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS operarios (
    id_operario       INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Datos personales. Convención hispana: nombre + apellido paterno + apellido materno.
    -- `apellido_materno` es nullable (extranjeros pueden no tener segundo apellido).
    nombre            TEXT    NOT NULL,
    apellido_paterno  TEXT    NOT NULL,
    apellido_materno  TEXT,

    -- Profesión: prefijo a mostrar antes del nombre en la UI ('Bioq.', 'Dr.', 'Tec.', 'Enf.', etc.).
    -- Nullable: no todos los operarios tienen título registrado.
    profesion         TEXT,

    -- Género: usado para resolver el saludo ('Bienvenido' vs 'Bienvenida').
    -- La población clínica del proyecto solo registra M o F. Nullable: se puede
    -- caer al saludo neutral si no se conoce.
    genero            TEXT    CHECK(genero IN ('M', 'F')),

    -- Credenciales.
    -- `usuario` UNIQUE: garantiza que no haya colisiones de login.
    -- `password_hash` almacena el hash bcrypt completo (formato `$2b$<cost>$<salt+hash>`),
    -- nunca el password en plano. Se compara con `bcrypt.checkpw`, nunca con `=`.
    usuario           TEXT    NOT NULL UNIQUE,
    password_hash     TEXT    NOT NULL,

    -- Rol del operario. CHECK garantiza que sólo sean valores válidos a nivel DB.
    rol               TEXT    NOT NULL CHECK(rol IN ('jefe', 'personal')),

    -- Soft-delete: en lugar de eliminar operarios físicamente (lo que rompería
    -- referencias futuras desde estudios), los marcamos como inactivos.
    activo            INTEGER NOT NULL DEFAULT 1,

    -- Auditoría temporal. SQLite almacena TIMESTAMP como TEXT (ISO 8601).
    fecha_creacion    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ultimo_acceso     TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_operarios_usuario ON operarios(usuario);


-- -----------------------------------------------------------------------------
-- Tabla: pacientes
-- -----------------------------------------------------------------------------
-- Pacientes del laboratorio. La identificación principal son los códigos del
-- hospital (`historia_clinica` y `id_paciente_hospital`); el documento de
-- identidad civil es opcional.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pacientes (
    id_paciente           INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Código alfanumérico de historia clínica del hospital. Identificador
    -- principal del paciente. NOT NULL UNIQUE: dos pacientes no pueden compartirlo.
    historia_clinica      TEXT    NOT NULL UNIQUE,

    -- ID del paciente en el sistema de archivos del hospital. Alfanumérico, admite '/'.
    -- Es el código que usa el área de archivo para rastrear documentación física.
    id_paciente_hospital  TEXT    NOT NULL UNIQUE,

    -- Datos demográficos.
    nombre                TEXT    NOT NULL,
    apellido_paterno      TEXT    NOT NULL,
    apellido_materno      TEXT,
    fecha_nacimiento      DATE,
    genero                TEXT    CHECK(genero IN ('M', 'F')),

    -- Documento civil (CI/DNI). Opcional. Si se registra, debe ser único.
    documento             TEXT    UNIQUE,

    fecha_creacion        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Índices para acelerar las búsquedas por los identificadores del hospital
-- (ya hay índice implícito por UNIQUE pero lo dejamos explícito por claridad).
CREATE INDEX IF NOT EXISTS idx_pacientes_historia_clinica ON pacientes(historia_clinica);
CREATE INDEX IF NOT EXISTS idx_pacientes_id_hospital      ON pacientes(id_paciente_hospital);


-- -----------------------------------------------------------------------------
-- Tabla: estudios
-- -----------------------------------------------------------------------------
-- Un estudio es la unidad de trabajo que hace un operario para un paciente:
-- agrupa las capturas tomadas con el microscopio + el análisis de IA + el
-- reporte generado.
--
-- El "estado" del estudio se infiere de las fechas:
--   * Pendiente:   fecha_analisis IS NULL
--   * Completado:  fecha_analisis IS NOT NULL
-- Si en el futuro necesitamos más estados (ej: "en revisión"), agregamos una
-- columna `estado` explícita.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS estudios (
    id_estudio         INTEGER PRIMARY KEY AUTOINCREMENT,

    id_paciente        INTEGER NOT NULL REFERENCES pacientes(id_paciente),
    id_operario        INTEGER NOT NULL REFERENCES operarios(id_operario),

    -- Código alfanumérico del registro de muestra del hospital. Cada muestra
    -- física tiene un ID único en el sistema interno; un estudio = una muestra.
    id_muestra         TEXT    NOT NULL UNIQUE,

    -- Procedencia de la muestra dentro del hospital (urgencias, consulta externa,
    -- internación, etc.). Código alfanumérico, obligatorio para trazabilidad clínica.
    procedencia        TEXT    NOT NULL,

    -- Cuándo se inició el estudio (al cargar la primera captura).
    fecha_creacion     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Cuándo se corrió el análisis de IA. NULL hasta que el operario lo dispara.
    fecha_analisis     TIMESTAMP,

    -- Tiempo que tardó el modelo en procesar el estudio, en segundos.
    -- Usado por el dashboard para mostrar "Tiempo promedio de análisis".
    duracion_segundos  REAL,

    -- Notas libres del operario sobre el estudio.
    observaciones      TEXT
);

CREATE INDEX IF NOT EXISTS idx_estudios_operario_fecha    ON estudios(id_operario, fecha_creacion);
CREATE INDEX IF NOT EXISTS idx_estudios_operario_analisis ON estudios(id_operario, fecha_analisis);
CREATE INDEX IF NOT EXISTS idx_estudios_paciente          ON estudios(id_paciente);


-- -----------------------------------------------------------------------------
-- Tabla: capturas
-- -----------------------------------------------------------------------------
-- Imágenes capturadas con el microscopio Swift Cam SCA-EA05. Un estudio puede
-- tener múltiples capturas (típicamente 1-10 campos del frotis).
--
-- ON DELETE CASCADE: si se borra el estudio, sus capturas se borran también
-- para evitar archivos huérfanos en disco apuntando a un id_estudio inexistente.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS capturas (
    id_captura     INTEGER PRIMARY KEY AUTOINCREMENT,
    id_estudio     INTEGER NOT NULL REFERENCES estudios(id_estudio) ON DELETE CASCADE,

    -- Path al archivo de imagen, RELATIVO a `data/capturas/`. Mantener relativo
    -- garantiza que mover/copiar el directorio del proyecto no rompa las refs.
    path_imagen    TEXT    NOT NULL,

    fecha_captura  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Notas libres por captura (ej: "campo central, ampliación 100x").
    notas          TEXT
);

CREATE INDEX IF NOT EXISTS idx_capturas_estudio ON capturas(id_estudio);


-- -----------------------------------------------------------------------------
-- Tabla: reportes
-- -----------------------------------------------------------------------------
-- Reportes PDF generados a partir de un estudio analizado. Un estudio puede
-- tener 0 o más reportes (regenerar el reporte crea un nuevo registro; no
-- sobreescribimos para mantener historial).
--
-- ON DELETE CASCADE: análogo al de capturas.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reportes (
    id_reporte         INTEGER PRIMARY KEY AUTOINCREMENT,
    id_estudio         INTEGER NOT NULL REFERENCES estudios(id_estudio) ON DELETE CASCADE,

    -- Path al PDF, RELATIVO a `data/reportes/`. Nullable: el registro existe
    -- desde que se solicita el reporte, el path se llena cuando el PDF se escribe.
    path_pdf           TEXT,

    fecha_generacion   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reportes_estudio ON reportes(id_estudio);
