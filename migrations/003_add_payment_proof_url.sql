-- Migration: Add payment_proof_url column to requests table
-- This stores the Cloudinary URL of the rider's proof of payment photo

ALTER TABLE requests ADD COLUMN payment_proof_url VARCHAR(500) NULL AFTER payment_status;
