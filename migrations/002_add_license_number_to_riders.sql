-- ================================================================================
-- ADD LICENSE NUMBER TO RIDERS TABLE
-- This migration adds a license_number column to store driver's license numbers
-- Date: February 5, 2026
-- ================================================================================

-- 1. Add license_number column to riders table
ALTER TABLE riders
ADD COLUMN license_number VARCHAR(50) DEFAULT NULL AFTER license_plate,
ADD INDEX idx_license_number (license_number);

-- 2. Rename license_plate to vehicle_plate if needed (optional - only if vehicle_plate is the correct name)
-- Note: This assumes license_plate should remain as-is for vehicle license plate

-- ================================================================================
-- VERIFICATION (Run these to check the changes)
-- ================================================================================

-- Verify riders table structure
-- DESCRIBE riders;
-- SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS 
-- WHERE TABLE_NAME = 'riders' AND (COLUMN_NAME = 'license_number' OR COLUMN_NAME = 'vehicle_plate');

-- ================================================================================
-- EXPECTED RESULT
-- ================================================================================
-- New column 'license_number' should be added to riders table
-- - Type: VARCHAR(50)
-- - Nullable: YES
-- - Default: NULL
