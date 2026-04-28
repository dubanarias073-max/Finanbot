-- ============================================
-- FINANBOT - Base de Datos
-- Gestor: MySQL Workbench
-- ============================================

CREATE DATABASE IF NOT EXISTS finanbot_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE finanbot_db;

-- ============================================
-- TABLA: usuarios
-- ============================================
CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    correo VARCHAR(150) NOT NULL UNIQUE,
    contrasena_hash VARCHAR(255) NOT NULL,
    ingreso_mensual DECIMAL(10,2) DEFAULT 0.00,
    meta_ahorro DECIMAL(10,2) DEFAULT 0.00,
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- TABLA: categorias
-- ============================================
CREATE TABLE categorias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(80) NOT NULL,
    tipo ENUM('gasto', 'ingreso') NOT NULL,
    icono VARCHAR(50)
);

-- Categorías predefinidas
INSERT INTO categorias (nombre, tipo, icono) VALUES
('Alimentación', 'gasto', '🍔'),
('Transporte', 'gasto', '🚌'),
('Arriendo', 'gasto', '🏠'),
('Salud', 'gasto', '💊'),
('Entretenimiento', 'gasto', '🎮'),
('Educación', 'gasto', '📚'),
('Ropa', 'gasto', '👕'),
('Servicios públicos', 'gasto', '💡'),
('Otros gastos', 'gasto', '💸'),
('Salario', 'ingreso', '💼'),
('Freelance', 'ingreso', '💻'),
('Otros ingresos', 'ingreso', '💰');

-- ============================================
-- TABLA: transacciones
-- ============================================
CREATE TABLE transacciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    categoria_id INT NOT NULL,
    tipo ENUM('gasto', 'ingreso') NOT NULL,
    monto DECIMAL(10,2) NOT NULL CHECK (monto > 0),
    descripcion VARCHAR(255),
    fecha DATE NOT NULL,
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (categoria_id) REFERENCES categorias(id)
);

-- ============================================
-- TABLA: metas_ahorro
-- ============================================
CREATE TABLE metas_ahorro (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    monto_objetivo DECIMAL(10,2) NOT NULL,
    monto_actual DECIMAL(10,2) DEFAULT 0.00,
    fecha_limite DATE,
    completada BOOLEAN DEFAULT FALSE,
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

-- ============================================
-- TABLA: simulaciones
-- ============================================
CREATE TABLE simulaciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    capital_inicial DECIMAL(12,2) NOT NULL,
    tasa_retorno DECIMAL(5,2) NOT NULL,
    plazo_meses INT NOT NULL,
    resultado_final DECIMAL(14,2) NOT NULL,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

-- ============================================
-- TABLA: chats
-- ============================================
CREATE TABLE chats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT,
    mensaje TEXT NOT NULL,
    respuesta TEXT NOT NULL,
    es_invitado BOOLEAN DEFAULT FALSE,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

