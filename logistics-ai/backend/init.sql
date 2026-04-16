-- Initialize Logistics AI Database Schema
-- This file runs automatically on first container startup

USE logistics_db;

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    email_hash VARCHAR(64) NOT NULL UNIQUE,
    encrypted_email TEXT NOT NULL,
    password_hash VARCHAR(512) NOT NULL,
    full_name VARCHAR(255),
    role ENUM('admin', 'operator', 'viewer') DEFAULT 'viewer',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP NULL,
    INDEX idx_username (username),
    INDEX idx_email_hash (email_hash),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Audit Logs Table
CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    action VARCHAR(255) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id INT,
    old_value JSON,
    new_value JSON,
    ip_address VARCHAR(45),
    user_agent VARCHAR(512),
    status ENUM('success', 'failure') DEFAULT 'success',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at),
    INDEX idx_resource (resource_type, resource_id),
    INDEX idx_action (action)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Shipment Events Log (for monitoring and analytics)
CREATE TABLE IF NOT EXISTS shipment_events (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    shipment_id VARCHAR(100) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_description TEXT,
    location VARCHAR(255),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    metadata JSON,
    severity ENUM('info', 'warning', 'critical') DEFAULT 'info',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_shipment_id (shipment_id),
    INDEX idx_event_type (event_type),
    INDEX idx_created_at (created_at),
    INDEX idx_severity (severity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Decision History Table
CREATE TABLE IF NOT EXISTS decision_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    shipment_id VARCHAR(100) NOT NULL,
    decision_type VARCHAR(100) NOT NULL,
    recommendation TEXT NOT NULL,
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 100),
    status ENUM('pending', 'approved', 'rejected', 'executed') DEFAULT 'pending',
    approved_by INT,
    approval_notes TEXT,
    executed_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX idx_shipment_id (shipment_id),
    INDEX idx_decision_type (decision_type),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- System Configuration Table
CREATE TABLE IF NOT EXISTS system_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    config_key VARCHAR(255) NOT NULL UNIQUE,
    config_value TEXT,
    config_type VARCHAR(50),
    is_encrypted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_config_key (config_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create default admin user (password should be set via registration endpoint in production)
-- email_hash: SHA-256('admin@logistics-ai.local')
-- encrypted_email: Fernet encrypted value (placeholder)
INSERT IGNORE INTO users (username, email_hash, encrypted_email, password_hash, full_name, role)
VALUES (
    'admin',
    '7ab2a51b90b4c1e0a06f90b5f8d7e8c9d0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c',
    'gAAAAABkL3x9placeholder_encrypted_email_value_here',
    '$2b$12$KIXxPfxeKo.B.jgR5hkTCO5N3/W.Q2CqAqhXZ8kPlZa.rOvmUL6s2',
    'System Administrator',
    'admin'
);

-- Create default configuration entries
INSERT IGNORE INTO system_config (config_key, config_value, config_type)
VALUES
    ('alert_threshold_high', '90', 'integer'),
    ('alert_threshold_medium', '75', 'integer'),
    ('alert_threshold_low', '50', 'integer'),
    ('max_shipment_delay_hours', '24', 'integer'),
    ('notification_enabled', 'true', 'boolean'),
    ('maintenance_mode', 'false', 'boolean');

-- Create indexes for better performance
CREATE INDEX idx_shipment_events_shipment_created ON shipment_events(shipment_id, created_at);
CREATE INDEX idx_decision_history_shipment_created ON decision_history(shipment_id, created_at);

-- Grant privileges
GRANT ALL PRIVILEGES ON logistics_db.* TO 'logistics_user'@'%';
FLUSH PRIVILEGES;
