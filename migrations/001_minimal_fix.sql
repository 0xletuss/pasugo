-- ================================================================================
-- MINIMAL CLOUDINARY MIGRATION - Safe for existing schemas
-- This script safely adds missing Cloudinary columns without errors
-- Date: February 5, 2026
-- ================================================================================

-- 1. Add profile_photo_url to users table (the main missing column causing errors)
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS profile_photo_url VARCHAR(500) DEFAULT NULL;

-- 2. id_document_url already exists in riders table (you got error: Duplicate column)
-- So we skip that

-- 3-5. The other columns (bill_photo_path, attachment_path) don't exist in source
-- So there's nothing to rename

-- ================================================================================
-- SUMMARY OF CHANGES
-- ================================================================================
-- Only change made: Added profile_photo_url to users table
-- (All other columns already exist or don't need migration)

-- ================================================================================
-- VERIFICATION
-- ================================================================================
-- Check if profile_photo_url exists in users
SELECT COUNT(*) as column_exists 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'users' AND COLUMN_NAME = 'profile_photo_url';

-- Should return 1 if successful
