-- Migration: Add reference_id and reference_type to notifications table
-- These columns are used by notification_helper.py to link notifications to requests

ALTER TABLE notifications ADD COLUMN reference_id INT NULL;
ALTER TABLE notifications ADD COLUMN reference_type VARCHAR(50) NULL;
