-- ================================================================================
-- CLOUDINARY DATABASE MIGRATION
-- Run this SQL on your Pasugo database to add Cloudinary URL columns
-- Date: February 5, 2026
-- ================================================================================

-- 1. Add profile_photo_url to users table
ALTER TABLE users 
ADD COLUMN profile_photo_url VARCHAR(500) DEFAULT NULL,
ADD INDEX idx_profile_photo_url (profile_photo_url);

-- 2. Add id_document_url to riders table  
ALTER TABLE riders
ADD COLUMN id_document_url VARCHAR(500) DEFAULT NULL,
ADD INDEX idx_id_document_url (id_document_url);

-- 3. Change bill_photo_path to bill_photo_url in bill_requests table
ALTER TABLE bill_requests
CHANGE COLUMN bill_photo_path bill_photo_url VARCHAR(500) DEFAULT NULL;

-- 4. Change attachment_path to attachment_url in complaints table
ALTER TABLE complaints
CHANGE COLUMN attachment_path attachment_url VARCHAR(500) DEFAULT NULL;

-- 5. Change attachment_path to attachment_url in complaint_replies table
ALTER TABLE complaint_replies
CHANGE COLUMN attachment_path attachment_url VARCHAR(500) DEFAULT NULL;

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
