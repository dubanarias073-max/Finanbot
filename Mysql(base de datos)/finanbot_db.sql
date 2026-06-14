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

-- =========================================================
-- INDICES
-- =========================================================

CREATE INDEX idx_transacciones_usuario_fecha
ON transacciones(usuario_id, fecha);

CREATE INDEX idx_transacciones_categoria
ON transacciones(categoria_id);

CREATE INDEX idx_chats_conversacion_fecha
ON chats(conversacion_id, fecha);

CREATE INDEX idx_metas_usuario
ON metas_ahorro(usuario_id);

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