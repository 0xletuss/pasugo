-- Migration 007: Create remittances table for daily rider remittance tracking
CREATE TABLE IF NOT EXISTS remittances (
    remittance_id INT AUTO_INCREMENT PRIMARY KEY,
    rider_id INT NOT NULL,
    remittance_date DATE NOT NULL,
    total_deliveries INT DEFAULT 0,
    total_service_fee DECIMAL(10, 2) DEFAULT 0.00,
    rider_share DECIMAL(10, 2) DEFAULT 0.00,
    admin_share DECIMAL(10, 2) DEFAULT 0.00,
    status ENUM('pending', 'remitted', 'waived') DEFAULT 'pending',
    remitted_at DATETIME NULL,
    received_by INT NULL,
    notes TEXT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (rider_id) REFERENCES riders(rider_id) ON DELETE CASCADE,
    FOREIGN KEY (received_by) REFERENCES users(user_id) ON DELETE SET NULL,
    INDEX idx_rider_id (rider_id),
    INDEX idx_remittance_date (remittance_date),
    INDEX idx_status (status),
    UNIQUE KEY uq_rider_date (rider_id, remittance_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
