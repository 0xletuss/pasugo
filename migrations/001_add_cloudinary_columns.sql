-- ================================================================================
-- CLOUDINARY DATABASE MIGRATION
-- Run this SQL on your Pasugo database to add Cloudinary URL columns
-- Date: February 5, 2026
-- ================================================================================

-- 1. Add profile_photo_url to users table (if not exists)
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS profile_photo_url VARCHAR(500) DEFAULT NULL;

-- Add index if column doesn't already have one
ALTER TABLE users 
ADD INDEX IF NOT EXISTS idx_profile_photo_url (profile_photo_url);

-- 2. Add id_document_url to riders table (if not exists)
ALTER TABLE riders
ADD COLUMN IF NOT EXISTS id_document_url VARCHAR(500) DEFAULT NULL;

-- Add index if column doesn't already have one
ALTER TABLE riders 
ADD INDEX IF NOT EXISTS idx_id_document_url (id_document_url);

-- 3. Change bill_photo_path to bill_photo_url in bill_requests table (if column exists)
-- First check if bill_photo_path exists, if so rename it
ALTER TABLE bill_requests
CHANGE COLUMN `bill_photo_path` `bill_photo_url` VARCHAR(500) DEFAULT NULL;

-- If above fails, it might already be named bill_photo_url or not exist
-- Ensure bill_photo_url exists
ALTER TABLE bill_requests
ADD COLUMN IF NOT EXISTS bill_photo_url VARCHAR(500) DEFAULT NULL;

-- 4. Change attachment_path to attachment_url in complaints table (if column exists)
-- First check if attachment_path exists, if so rename it
ALTER TABLE complaints
CHANGE COLUMN `attachment_path` `attachment_url` VARCHAR(500) DEFAULT NULL;

-- If above fails, it might already be named attachment_url or not exist
-- Ensure attachment_url exists
ALTER TABLE complaints
ADD COLUMN IF NOT EXISTS attachment_url VARCHAR(500) DEFAULT NULL;

-- 5. Change attachment_path to attachment_url in complaint_replies table (if column exists)
-- First check if attachment_path exists, if so rename it
ALTER TABLE complaint_replies
CHANGE COLUMN `attachment_path` `attachment_url` VARCHAR(500) DEFAULT NULL;

-- If above fails, it might already be named attachment_url or not exist
-- Ensure attachment_url exists
ALTER TABLE complaint_replies
ADD COLUMN IF NOT EXISTS attachment_url VARCHAR(500) DEFAULT NULL;

-- ================================================================================
-- VERIFICATION (Run these to check the changes)
-- ================================================================================

-- Verify users table
-- DESCRIBE users;
-- SELECT COLUMN_NAME, COLUMN_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'users' AND COLUMN_NAME = 'profile_photo_url';

-- Verify riders table
-- DESCRIBE riders;
-- SELECT COLUMN_NAME, COLUMN_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'riders' AND COLUMN_NAME = 'id_document_url';

-- Verify bill_requests table
-- SELECT COLUMN_NAME, COLUMN_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'bill_requests' AND COLUMN_NAME = 'bill_photo_url';

-- ================================================================================
-- EXPECTED RESULT
-- ================================================================================
-- All commands should complete without errors
-- Each table will have one new/modified column:
-- - users.profile_photo_url (VARCHAR 500)
-- - riders.id_document_url (VARCHAR 500)
-- - bill_requests.bill_photo_url (VARCHAR 500)
-- - complaints.attachment_url (VARCHAR 500)
-- - complaint_replies.attachment_url (VARCHAR 500)
