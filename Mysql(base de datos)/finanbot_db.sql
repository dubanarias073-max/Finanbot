-- =========================================================
-- FINANBOT DATABASE (desde cero)
-- Incluye: catálogo de CATEGORÍAS, CATEGORÍAS POR USUARIO
-- (personalizadas u ocultas desde finanzas.html) y TIENDAS
-- (lugares con ubicación que se eligen en finanzas.html)
--
-- ⚠️ Borra finanbot_db si ya existe. No lo ejecutes sobre una
--    base con datos que quieras conservar.
-- =========================================================

-- Emojis de los iconos: el cliente debe enviar utf8mb4
SET NAMES utf8mb4;
SET time_zone = '-05:00';

DROP DATABASE IF EXISTS finanbot_db;

CREATE DATABASE finanbot_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE finanbot_db;

-- =========================================================
-- USUARIOS (rol = perfil elegido en el onboarding)
-- =========================================================

CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    correo VARCHAR(150) NOT NULL UNIQUE,
    contrasena_hash VARCHAR(255) NOT NULL,
    rol ENUM('estudiante','empleado','independiente','emprendedor') NULL,  -- NULL hasta completar el onboarding
    ingreso_mensual DECIMAL(10,2) DEFAULT 0.00,
    fecha_salario DATE NULL,  -- también define el "día de pago" (día del mes) usado en onboarding.html / perfil.html
    meta_ahorro DECIMAL(10,2) DEFAULT 0.00,
    onboarding_completado BOOLEAN DEFAULT FALSE,
    pregunta_seguridad VARCHAR(255),
    respuesta_seguridad VARCHAR(255),
    token_version INT NOT NULL DEFAULT 0,
    requiere_cambio_contrasena BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE login_alert_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    token_hash CHAR(64) NOT NULL UNIQUE,
    expires_at DATETIME NOT NULL,
    used_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_login_alert_tokens_usuario_id (usuario_id),
    CONSTRAINT fk_login_alert_tokens_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

CREATE TABLE password_reset_links (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    token_hash CHAR(64) NOT NULL UNIQUE,
    expires_at DATETIME NOT NULL,
    used_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_password_reset_links_usuario_id (usuario_id),
    CONSTRAINT fk_password_reset_links_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

-- =========================================================
-- CATEGORÍAS (catálogo general)
--   tipo 'gasto' | 'ingreso' | 'meta' (movimientos de perfil.html)
--   transacciones.categoria se une a categorias.nombre (FK).
--   Las categorías que crean los usuarios también se guardan
--   aquí (para que la FK funcione) y se enlazan al usuario en
--   la tabla categorias_usuario.
-- =========================================================

CREATE TABLE categorias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    tipo ENUM('gasto','ingreso','meta') NOT NULL,
    icono VARCHAR(10) NOT NULL,
    INDEX idx_categorias_tipo (tipo)
);

INSERT INTO categorias (nombre, tipo, icono) VALUES
    -- Gastos
    ('Alimentación','gasto','🍔'),
    ('Transporte','gasto','🚌'),
    ('Arriendo','gasto','🏠'),
    ('Salud','gasto','💊'),
    ('Entretenimiento','gasto','🎬'),
    ('Educación','gasto','📚'),
    ('Ropa','gasto','👗'),
    ('Servicios','gasto','⚡'),
    ('Mascotas','gasto','🐾'),
    ('Regalos','gasto','🎁'),
    ('Viajes','gasto','✈️'),
    ('Otros gastos','gasto','📦'),
    -- Ingresos
    ('Salario','ingreso','💼'),
    ('Freelance','ingreso','🧑‍💻'),
    ('Inversión','ingreso','📈'),
    ('Negocio','ingreso','🏪'),
    ('Regalo','ingreso','🎁'),
    ('Otros ingresos','ingreso','💵'),
    -- Metas de ahorro
    ('Ahorro automático','meta','🎯'),
    ('Aporte manual a meta','meta','🎯'),
    ('Ajuste de meta','meta','🎯'),
    ('Retiro de ahorro','meta','↩️');

-- =========================================================
-- CATEGORÍAS POR USUARIO (botón "Categorías" de finanzas.html)
--   personalizada = TRUE  → la creó el usuario (ej. ☕ Café)
--   personalizada = FALSE → categoría predeterminada que el usuario
--                           ocultó (oculta) o eliminó (eliminada).
--   Al eliminar una categoría, los movimientos pasan a 'Otros gastos'
--   / 'Otros ingresos'; la eliminación es individual por usuario.
-- =========================================================

CREATE TABLE categorias_usuario (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    nombre VARCHAR(50) NOT NULL,
    tipo ENUM('gasto','ingreso') NOT NULL,
    icono VARCHAR(10) NOT NULL DEFAULT '🏷️',
    personalizada BOOLEAN NOT NULL DEFAULT TRUE,
    oculta BOOLEAN NOT NULL DEFAULT FALSE,
    eliminada BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id)
        ON DELETE CASCADE,
    FOREIGN KEY (nombre)
        REFERENCES categorias(nombre)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    UNIQUE KEY uq_categoria_usuario_nombre (usuario_id, nombre),
    INDEX idx_categorias_usuario_usuario (usuario_id)
);

-- =========================================================
-- TIENDAS (lugares donde el usuario hace sus movimientos)
-- Se llena sola: cada vez que una transacción trae ubicación
-- (ubicacion_nombre + latitud + longitud) un trigger crea la
-- tienda si no existe y la enlaza con tienda_id.
-- =========================================================

CREATE TABLE tiendas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    latitud DECIMAL(10,7) NOT NULL,
    longitud DECIMAL(10,7) NOT NULL,
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id)
        ON DELETE CASCADE,
    UNIQUE KEY uq_tienda_usuario_nombre (usuario_id, nombre),
    INDEX idx_tiendas_coords (usuario_id, latitud, longitud)
);

-- =========================================================
-- TRANSACCIONES
--   Gastos:   Alimentación, Transporte, Arriendo, Salud, Entretenimiento,
--             Educación, Ropa, Servicios, Mascotas, Regalos, Viajes, Otros gastos
--   Ingresos: Salario, Freelance, Inversión, Negocio, Regalo, Otros ingresos
--   Metas (perfil.html): Ahorro automático, Aporte manual a meta,
--             Ajuste de meta, Retiro de ahorro
-- Se conservan categoria / ubicacion_nombre / latitud / longitud
-- para que el backend y el front sigan funcionando igual;
-- tienda_id se asigna automáticamente con los triggers.
-- =========================================================

CREATE TABLE transacciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    categoria VARCHAR(50) NOT NULL,   -- unida a categorias(nombre) por FOREIGN KEY
    tipo ENUM('gasto','ingreso') NOT NULL,
    monto DECIMAL(10,2) NOT NULL,
    descripcion VARCHAR(255),
    fecha DATE NOT NULL,
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
    -- Ubicación donde se hizo el movimiento (opcional, se ve en el mapa)
    ubicacion_nombre VARCHAR(255) NULL,
    latitud DECIMAL(10,7) NULL,
    longitud DECIMAL(10,7) NULL,
    -- Tienda/lugar enlazado (lo llenan los triggers)
    tienda_id INT NULL,

    FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id)
        ON DELETE CASCADE,
    FOREIGN KEY (categoria)
        REFERENCES categorias(nombre)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (tienda_id)
        REFERENCES tiendas(id)
        ON DELETE SET NULL,
    INDEX idx_transacciones_ubicacion (usuario_id, latitud, longitud)
);

-- =========================================================
-- TRIGGERS: crean/enlazan la tienda automáticamente
-- =========================================================

DELIMITER $$

CREATE TRIGGER trg_transacciones_tienda_ins
BEFORE INSERT ON transacciones
FOR EACH ROW
BEGIN
    DECLARE v_tienda INT;
    IF NEW.ubicacion_nombre IS NOT NULL AND TRIM(NEW.ubicacion_nombre) <> ''
       AND NEW.latitud IS NOT NULL AND NEW.longitud IS NOT NULL THEN
        INSERT IGNORE INTO tiendas (usuario_id, nombre, latitud, longitud)
        VALUES (NEW.usuario_id, NEW.ubicacion_nombre, NEW.latitud, NEW.longitud);
        SELECT id INTO v_tienda FROM tiendas
        WHERE usuario_id = NEW.usuario_id AND nombre = NEW.ubicacion_nombre
        LIMIT 1;
        SET NEW.tienda_id = v_tienda;
    END IF;
END$$

CREATE TRIGGER trg_transacciones_tienda_upd
BEFORE UPDATE ON transacciones
FOR EACH ROW
BEGIN
    DECLARE v_tienda INT;
    IF NEW.ubicacion_nombre IS NOT NULL AND TRIM(NEW.ubicacion_nombre) <> ''
       AND NEW.latitud IS NOT NULL AND NEW.longitud IS NOT NULL THEN
        INSERT IGNORE INTO tiendas (usuario_id, nombre, latitud, longitud)
        VALUES (NEW.usuario_id, NEW.ubicacion_nombre, NEW.latitud, NEW.longitud);
        SELECT id INTO v_tienda FROM tiendas
        WHERE usuario_id = NEW.usuario_id AND nombre = NEW.ubicacion_nombre
        LIMIT 1;
        SET NEW.tienda_id = v_tienda;
    ELSE
        SET NEW.tienda_id = NULL;   -- se quitó la ubicación
    END IF;
END$$

DELIMITER ;

-- =========================================================
-- METAS: ahorro y límites de gasto por mes/año
-- =========================================================

CREATE TABLE meta (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    monto_objetivo DECIMAL(10,2) NOT NULL,
    monto_actual DECIMAL(10,2) DEFAULT 0.00,
    fecha_limite DATE,
    completada BOOLEAN DEFAULT FALSE,
    tipo ENUM('ahorro','gasto_mensual','gasto_anual') NOT NULL DEFAULT 'ahorro',
    modo ENUM('manual','automatico') NOT NULL DEFAULT 'manual',
    monto_automatico DECIMAL(10,2) NULL,
    dia_automatico INT NULL,
    icono VARCHAR(10) NULL,
    categoria VARCHAR(50) NULL,
    prioridad VARCHAR(10) NOT NULL DEFAULT 'media',
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id)
        ON DELETE CASCADE
);

-- =========================================================
-- CHATS (chats + conversaciones unidas en una sola tabla)
-- Cada fila es un mensaje. Los mensajes de una misma
-- conversación comparten conversacion_id (UUID generado
-- por el backend) y titulo.
-- =========================================================

CREATE TABLE chats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NULL,
    conversacion_id CHAR(36) NOT NULL,
    titulo VARCHAR(100) DEFAULT 'Nueva conversación',
    mensaje TEXT NOT NULL,
    respuesta TEXT NOT NULL,
    es_invitado BOOLEAN DEFAULT FALSE,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id)
        ON DELETE SET NULL
);

-- =========================================================
-- INDICES
-- =========================================================

CREATE INDEX idx_usuarios_rol
ON usuarios(rol);

CREATE INDEX idx_transacciones_usuario_fecha
ON transacciones(usuario_id, fecha);

CREATE INDEX idx_transacciones_usuario_tipo
ON transacciones(usuario_id, tipo);

CREATE INDEX idx_transacciones_usuario_categoria
ON transacciones(usuario_id, categoria);

CREATE INDEX idx_transacciones_tienda
ON transacciones(tienda_id);

CREATE INDEX idx_chats_usuario_fecha
ON chats(usuario_id, fecha);

CREATE INDEX idx_chats_conversacion_fecha
ON chats(conversacion_id, fecha);

CREATE INDEX idx_metas_usuario
ON meta(usuario_id);

CREATE INDEX idx_metas_usuario_completada
ON meta(usuario_id, completada);

-- =========================================================
-- VISTAS DE LECTURA
-- =========================================================

-- USUARIOS (sin contraseña ni pregunta/respuesta de seguridad)
CREATE VIEW vista_usuarios AS
SELECT
    id,
    nombre,
    correo,
    rol,
    ingreso_mensual,
    fecha_salario,
    meta_ahorro,
    onboarding_completado,
    fecha_registro
FROM usuarios;

-- TRANSACCIONES + usuario + categoría (con icono) + tienda
CREATE VIEW vista_transacciones AS
SELECT
    t.id,
    t.usuario_id,
    u.nombre AS usuario_nombre,
    t.categoria,
    c.icono AS categoria_icono,
    t.tipo,
    t.monto,
    t.descripcion,
    t.fecha,
    t.fecha_registro,
    t.tienda_id,
    ti.nombre AS tienda,
    t.latitud,
    t.longitud
FROM transacciones t
JOIN usuarios u ON u.id = t.usuario_id
LEFT JOIN categorias c ON c.nombre = t.categoria
LEFT JOIN tiendas ti ON ti.id = t.tienda_id;

-- TIENDAS con totales (equivale al ranking "lugares con más movimiento" del mapa)
CREATE VIEW vista_tiendas AS
SELECT
    ti.id,
    ti.usuario_id,
    u.nombre AS usuario_nombre,
    ti.nombre AS tienda,
    ti.latitud,
    ti.longitud,
    COUNT(t.id) AS total_movimientos,
    COALESCE(SUM(CASE WHEN t.tipo = 'gasto'   THEN t.monto END), 0) AS total_gastos,
    COALESCE(SUM(CASE WHEN t.tipo = 'ingreso' THEN t.monto END), 0) AS total_ingresos,
    MAX(t.fecha) AS ultimo_movimiento
FROM tiendas ti
JOIN usuarios u ON u.id = ti.usuario_id
LEFT JOIN transacciones t ON t.tienda_id = ti.id
GROUP BY ti.id, ti.usuario_id, u.nombre, ti.nombre, ti.latitud, ti.longitud;

-- CATEGORÍAS con totales por usuario
CREATE VIEW vista_categorias_usuario AS
SELECT
    t.usuario_id,
    c.nombre AS categoria,
    c.icono,
    c.tipo AS tipo_categoria,
    COUNT(*) AS total_movimientos,
    SUM(t.monto) AS total_monto
FROM transacciones t
JOIN categorias c ON c.nombre = t.categoria
GROUP BY t.usuario_id, c.nombre, c.icono, c.tipo;

-- CATEGORÍAS QUE VE CADA USUARIO en sus listas
-- (las de FinanBot que no ocultó + las que creó él)
CREATE VIEW vista_mis_categorias AS
SELECT
    u.id AS usuario_id,
    c.nombre,
    c.tipo,
    c.icono,
    FALSE AS personalizada
FROM usuarios u
JOIN categorias c ON c.tipo IN ('gasto','ingreso')
LEFT JOIN categorias_usuario cu
       ON cu.usuario_id = u.id AND cu.nombre = c.nombre AND cu.personalizada = FALSE
WHERE c.nombre NOT IN (SELECT nombre FROM categorias_usuario WHERE personalizada = TRUE)
  AND (cu.id IS NULL OR (cu.oculta = FALSE AND cu.eliminada = FALSE))
UNION ALL
SELECT
    cu.usuario_id,
    cu.nombre,
    cu.tipo,
    cu.icono,
    TRUE AS personalizada
FROM categorias_usuario cu
WHERE cu.personalizada = TRUE AND cu.oculta = FALSE AND cu.eliminada = FALSE;

-- METAS DE AHORRO + usuario
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
    m.tipo,
    m.modo,
    m.monto_automatico,
    m.dia_automatico,
    m.fecha_creacion
FROM meta m
JOIN usuarios u ON u.id = m.usuario_id;

-- CHATS (mensajes) + nombre de usuario
CREATE VIEW vista_chats AS
SELECT
    ch.id,
    ch.usuario_id,
    u.nombre AS usuario_nombre,
    ch.conversacion_id,
    ch.titulo,
    ch.mensaje,
    ch.respuesta,
    ch.es_invitado,
    ch.fecha
FROM chats ch
LEFT JOIN usuarios u ON u.id = ch.usuario_id;

-- CONVERSACIONES (derivadas de chats: una fila por conversación)
CREATE VIEW vista_conversaciones AS
SELECT
    ch.conversacion_id,
    ch.usuario_id,
    u.nombre             AS usuario_nombre,
    MAX(ch.titulo)       AS titulo,
    COUNT(*)             AS total_mensajes,
    MIN(ch.fecha)        AS fecha_creacion,
    MAX(ch.fecha)        AS fecha_actualizacion
FROM chats ch
LEFT JOIN usuarios u ON u.id = ch.usuario_id
GROUP BY ch.conversacion_id, ch.usuario_id, u.nombre;

-- =========================================================
-- DATOS DE PRUEBA (opcional)
-- =========================================================

-- INSERT INTO usuarios (nombre, correo, contrasena_hash, rol)
-- VALUES ('Prueba', 'prueba@finanbot.com', 'HASH_AQUI', 'estudiante');

-- INSERT INTO transacciones (usuario_id, categoria, tipo, monto, descripcion, fecha, ubicacion_nombre, latitud, longitud)
-- VALUES (1, 'Alimentación', 'gasto', 15000.00, 'Almuerzo', CURDATE(), 'Éxito Chapinero', 4.6486000, -74.0628000);
-- (la tienda "Éxito Chapinero" se crea sola en la tabla tiendas)

-- INSERT INTO categorias (nombre, tipo, icono) VALUES ('Café', 'gasto', '☕');
-- INSERT INTO categorias_usuario (usuario_id, nombre, tipo, icono) VALUES (1, 'Café', 'gasto', '☕');
-- (categoría personalizada "☕ Café" del usuario 1)

-- INSERT INTO chats (usuario_id, conversacion_id, titulo, mensaje, respuesta)
-- VALUES (1, UUID(), 'Mi primera conversación', 'Hola', '¡Hola! ¿En qué te ayudo?');

-- =========================================================
-- CONSULTAS DE EJEMPLO
-- =========================================================

-- SELECT * FROM categorias;
-- SELECT * FROM categorias WHERE tipo = 'gasto';
-- SELECT * FROM vista_mis_categorias WHERE usuario_id = 1;                        -- categorías que ve el usuario
-- SELECT * FROM categorias_usuario WHERE usuario_id = 1;                         -- sus personalizadas y ocultas
-- SELECT * FROM tiendas WHERE usuario_id = 1;
-- SELECT * FROM vista_tiendas WHERE usuario_id = 1 ORDER BY total_gastos DESC;   -- lugares donde más gastas
-- SELECT * FROM vista_categorias_usuario WHERE usuario_id = 1 ORDER BY total_monto DESC;
-- SELECT * FROM vista_transacciones;
-- SELECT * FROM vista_usuarios;
-- SELECT * FROM vista_metas_ahorro;
-- SELECT * FROM vista_chats;
-- SELECT * FROM vista_conversaciones;

-- Mensajes de una conversación en orden:
-- SELECT * FROM chats WHERE conversacion_id = '...' ORDER BY fecha;