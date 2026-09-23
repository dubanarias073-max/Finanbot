-- =========================================================
-- FINANBOT DATABASE (desde cero)
-- =========================================================

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
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- TRANSACCIONES (categoría como ENUM, ya no hay tabla categorias)
--   Gastos:   Alimentación, Transporte, Arriendo, Salud, Entretenimiento,
--             Educación, Ropa, Servicios, Mascotas, Regalos, Viajes, Otros gastos
--   Ingresos: Salario, Freelance, Inversión, Negocio, Regalo, Otros ingresos
--   Metas (perfil.html): Ahorro automático, Aporte manual a meta,
--             Ajuste de meta, Retiro de ahorro
-- =========================================================

CREATE TABLE transacciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    categoria ENUM(
        'Alimentación','Transporte','Arriendo','Salud','Entretenimiento','Educación',
        'Ropa','Servicios','Mascotas','Regalos','Viajes','Otros gastos',
        'Salario','Freelance','Inversión','Negocio','Regalo','Otros ingresos',
        'Ahorro automático','Aporte manual a meta','Ajuste de meta','Retiro de ahorro'
    ) NOT NULL,
    tipo ENUM('gasto','ingreso') NOT NULL,
    monto DECIMAL(10,2) NOT NULL,
    descripcion VARCHAR(255),
    fecha DATE NOT NULL,
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id)
        ON DELETE CASCADE
);

-- =========================================================
-- METAS DE AHORRO (incluye modo automático)
-- =========================================================

CREATE TABLE metas_ahorro (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    monto_objetivo DECIMAL(10,2) NOT NULL,
    monto_actual DECIMAL(10,2) DEFAULT 0.00,
    fecha_limite DATE,
    completada BOOLEAN DEFAULT FALSE,
    modo ENUM('manual','automatico') NOT NULL DEFAULT 'manual',
    monto_automatico DECIMAL(10,2) NULL,
    dia_automatico INT NULL,
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

CREATE INDEX idx_chats_usuario_fecha
ON chats(usuario_id, fecha);

CREATE INDEX idx_chats_conversacion_fecha
ON chats(conversacion_id, fecha);

CREATE INDEX idx_metas_usuario
ON metas_ahorro(usuario_id);

CREATE INDEX idx_metas_usuario_completada
ON metas_ahorro(usuario_id, completada);

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

-- TRANSACCIONES + usuario
CREATE VIEW vista_transacciones AS
SELECT
    t.id,
    t.usuario_id,
    u.nombre AS usuario_nombre,
    t.categoria,
    t.tipo,
    t.monto,
    t.descripcion,
    t.fecha,
    t.fecha_registro
FROM transacciones t
JOIN usuarios u ON u.id = t.usuario_id;

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
    m.modo,
    m.monto_automatico,
    m.dia_automatico,
    m.fecha_creacion
FROM metas_ahorro m
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

-- INSERT INTO transacciones (usuario_id, categoria, tipo, monto, descripcion, fecha)
-- VALUES (1, 'Alimentación', 'gasto', 15000.00, 'Almuerzo', CURDATE());

-- INSERT INTO chats (usuario_id, conversacion_id, titulo, mensaje, respuesta)
-- VALUES (1, UUID(), 'Mi primera conversación', 'Hola', '¡Hola! ¿En qué te ayudo?');

-- =========================================================
-- CONSULTAS DE EJEMPLO
-- =========================================================

-- SELECT * FROM vista_usuarios;
-- SELECT * FROM vista_transacciones;
-- SELECT * FROM vista_metas_ahorro;
-- SELECT * FROM vista_chats;
-- SELECT * FROM vista_conversaciones;

-- Mensajes de una conversación en orden:
-- SELECT * FROM chats WHERE conversacion_id = '...' ORDER BY fecha;