-- =========================================================
-- FINANBOT DATABASE
-- =========================================================

DROP DATABASE IF EXISTS finanbot_db;

CREATE DATABASE finanbot_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE finanbot_db;

-- =========================================================
-- USUARIOS
-- =========================================================

CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    correo VARCHAR(150) NOT NULL UNIQUE,
    contrasena_hash VARCHAR(255) NOT NULL,
    ingreso_mensual DECIMAL(10,2) DEFAULT 0.00,
    fecha_salario DATE NULL,  -- también define el "día de pago" (día del mes) usado en onboarding.html / perfil.html
    meta_ahorro DECIMAL(10,2) DEFAULT 0.00,
    onboarding_completado BOOLEAN DEFAULT FALSE,
    pregunta_seguridad VARCHAR(255),
    respuesta_seguridad VARCHAR(255),
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- CATEGORIAS
-- =========================================================

CREATE TABLE categorias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(80) NOT NULL,
    tipo ENUM('gasto','ingreso') NOT NULL,
    icono VARCHAR(50) NOT NULL
);

-- =========================================================
-- TRANSACCIONES
-- =========================================================

CREATE TABLE transacciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    categoria_id INT NOT NULL,
    tipo ENUM('gasto','ingreso') NOT NULL,
    monto DECIMAL(10,2) NOT NULL,
    descripcion VARCHAR(255),
    fecha DATE NOT NULL,
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id)
        ON DELETE CASCADE,

    FOREIGN KEY (categoria_id)
        REFERENCES categorias(id)
        ON DELETE RESTRICT
);

-- =========================================================
-- METAS DE AHORRO
-- =========================================================

CREATE TABLE metas_ahorro (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    monto_objetivo DECIMAL(10,2) NOT NULL,
    monto_actual DECIMAL(10,2) DEFAULT 0.00,
    fecha_limite DATE,
    completada BOOLEAN DEFAULT FALSE,
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id)
        ON DELETE CASCADE
);

-- =========================================================
-- PERIODOS FINANCIEROS (resumen mensual / "Ver mis finanzas por mes")
-- =========================================================

CREATE TABLE periodos_financieros (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    anio INT NOT NULL,
    mes INT NOT NULL,
    activo BOOLEAN DEFAULT TRUE,
    ingresos_total DECIMAL(10,2) DEFAULT 0.00,
    gastos_total DECIMAL(10,2) DEFAULT 0.00,
    balance DECIMAL(10,2) DEFAULT 0.00,
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_cierre DATETIME NULL,

    FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id)
        ON DELETE CASCADE
);

-- =========================================================
-- CONVERSACIONES
-- =========================================================

CREATE TABLE conversaciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    titulo VARCHAR(100) DEFAULT 'Nueva conversación',
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id)
        ON DELETE CASCADE
);

-- =========================================================
-- CHATS
-- =========================================================

CREATE TABLE chats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT,
    conversacion_id INT,
    mensaje TEXT NOT NULL,
    respuesta TEXT NOT NULL,
    es_invitado BOOLEAN DEFAULT FALSE,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id)
        ON DELETE SET NULL,

    FOREIGN KEY (conversacion_id)
        REFERENCES conversaciones(id)
        ON DELETE CASCADE
);

ALTER TABLE metas_ahorro
  ADD COLUMN modo VARCHAR(20) DEFAULT 'manual',
  ADD COLUMN monto_automatico DECIMAL(12,2) NULL,
  ADD COLUMN dia_automatico INT NULL;
-- =========================================================
-- INDICES
-- =========================================================

CREATE INDEX idx_transacciones_usuario_fecha
ON transacciones(usuario_id, fecha);

-- Cubre la calculadora financiera que filtra por usuario_id + tipo
-- ('gasto'/'ingreso') antes de sumar montos — ver models.py Transaccion.
CREATE INDEX idx_transacciones_usuario_tipo
ON transacciones(usuario_id, tipo);

CREATE INDEX idx_transacciones_categoria
ON transacciones(categoria_id);

-- Listar mensajes de un usuario ordenados por fecha (historial de chat
-- fuera de una conversación específica) — ver models.py Chat.
CREATE INDEX idx_chats_usuario_fecha
ON chats(usuario_id, fecha);

CREATE INDEX idx_chats_conversacion_fecha
ON chats(conversacion_id, fecha);

CREATE INDEX idx_metas_usuario
ON metas_ahorro(usuario_id);

-- Filtrar metas activas vs completadas de un usuario sin tabla completa
-- — ver models.py MetaAhorro / consulta_metas en finanbot_ia.py.
CREATE INDEX idx_metas_usuario_completada
ON metas_ahorro(usuario_id, completada);

-- Encontrar el periodo activo de un usuario para un mes dado sin
-- recorrer toda la tabla — ver gestionar_periodo_mensual en
-- routes/transacciones.py.
CREATE INDEX idx_periodos_usuario_activo
ON periodos_financieros(usuario_id, activo);

CREATE INDEX idx_periodos_usuario_anio_mes
ON periodos_financieros(usuario_id, anio, mes);

-- =========================================================
-- CATEGORIAS INICIALES
-- =========================================================

INSERT INTO categorias (nombre, tipo, icono) VALUES
('Alimentación',    'gasto',   '🍔'),
('Transporte',      'gasto',   '🚌'),
('Arriendo',        'gasto',   '🏠'),
('Salud',           'gasto',   '💊'),
('Entretenimiento', 'gasto',   '🎬'),
('Educación',       'gasto',   '📚'),
('Ropa',            'gasto',   '👗'),
('Servicios',       'gasto',   '⚡'),
('Mascotas',        'gasto',   '🐾'),
('Regalos',         'gasto',   '🎁'),
('Viajes',          'gasto',   '✈️'),
('Otros gastos',    'gasto',   '📦'),
('Salario',         'ingreso', '💼'),
('Freelance',       'ingreso', '💻'),
('Otros ingresos',  'ingreso', '💰');

-- =========================================================
-- VISTAS DE LECTURA (nombres legibles en vez de solo ids)
-- Las tablas base no cambian, así que el backend no necesita
-- tocarse: estas vistas son solo para consultar/inspeccionar
-- la base de datos con SELECT * y ver nombres en lugar de ids.
-- =========================================================

-- USUARIOS (sin datos sensibles: nunca expone contrasena_hash ni la
-- pregunta/respuesta de seguridad, ni siquiera para consulta manual)
CREATE VIEW vista_usuarios AS
SELECT
    id,
    nombre,
    correo,
    ingreso_mensual,
    fecha_salario,
    meta_ahorro,
    onboarding_completado,
    fecha_registro
FROM usuarios;

-- CATEGORIAS (la tabla ya es legible por sí sola — se agrega la vista
-- solo por consistencia con el resto)
CREATE VIEW vista_categorias AS
SELECT
    id,
    nombre,
    tipo,
    icono
FROM categorias;

-- TRANSACCIONES + nombre de usuario + nombre de categoría
CREATE VIEW vista_transacciones AS
SELECT
    t.id,
    t.usuario_id,
    u.nombre AS usuario_nombre,
    t.categoria_id,
    c.nombre AS categoria,
    c.icono,
    t.tipo,
    t.monto,
    t.descripcion,
    t.fecha,
    t.fecha_registro
FROM transacciones t
JOIN usuarios u    ON u.id = t.usuario_id
JOIN categorias c  ON c.id = t.categoria_id;

-- METAS DE AHORRO + nombre de usuario
CREATE VIEW vista_metas_ahorro AS
SELECT
    m.id,
    m.usuario_id,
    u.nombre AS usuario_nombre,
    m.nombre AS meta,
    m.monto_objetivo,
    m.monto_actual,
    m.fecha_limite,
    m.completada,
    m.fecha_creacion
FROM metas_ahorro m
JOIN usuarios u ON u.id = m.usuario_id;

-- PERIODOS FINANCIEROS + nombre de usuario
CREATE VIEW vista_periodos_financieros AS
SELECT
    p.id,
    p.usuario_id,
    u.nombre AS usuario_nombre,
    p.anio,
    p.mes,
    p.activo,
    p.ingresos_total,
    p.gastos_total,
    p.balance,
    p.fecha_creacion,
    p.fecha_cierre
FROM periodos_financieros p
JOIN usuarios u ON u.id = p.usuario_id;

-- CONVERSACIONES + nombre de usuario
CREATE VIEW vista_conversaciones AS
SELECT
    conv.id,
    conv.usuario_id,
    u.nombre AS usuario_nombre,
    conv.titulo,
    conv.fecha_creacion,
    conv.fecha_actualizacion
FROM conversaciones conv
JOIN usuarios u ON u.id = conv.usuario_id;

-- CHATS + nombre de usuario (usuario_id puede ser NULL si el chat fue de un invitado)
CREATE VIEW vista_chats AS
SELECT
    ch.id,
    ch.usuario_id,
    u.nombre AS usuario_nombre,
    ch.conversacion_id,
    ch.mensaje,
    ch.respuesta,
    ch.es_invitado,
    ch.fecha
FROM chats ch
LEFT JOIN usuarios u ON u.id = ch.usuario_id;

-- =========================================================
-- CONSULTAS DE EJEMPLO — un SELECT por cada tabla y cada vista
-- Descoméntalas / cópialas según lo que quieras revisar.
-- =========================================================

-- Tablas base
-- SELECT * FROM usuarios;
-- SELECT * FROM categorias;
-- SELECT * FROM transacciones;
-- SELECT * FROM metas_ahorro;
-- SELECT * FROM periodos_financieros;
-- SELECT * FROM conversaciones;
-- SELECT * FROM chats;

-- Vistas (nombres legibles)
-- SELECT * FROM vista_usuarios;
-- SELECT * FROM vista_categorias;
-- SELECT * FROM vista_transacciones;
-- SELECT * FROM vista_metas_ahorro;
-- SELECT * FROM vista_periodos_financieros;
-- SELECT * FROM vista_conversaciones;
-- SELECT * FROM vista_chats;
