-- Migration: Add GCash payment info fields to riders table
-- Date: 2026-02-18

ALTER TABLE riders ADD COLUMN IF NOT EXISTS gcash_name VARCHAR(255) NULL;
ALTER TABLE riders ADD COLUMN IF NOT EXISTS gcash_number VARCHAR(20) NULL;
