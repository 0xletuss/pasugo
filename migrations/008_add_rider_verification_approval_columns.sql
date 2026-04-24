-- Rider verification and admin approval flow
-- Run this in Aiven MySQL before starting the updated backend.

ALTER TABLE riders
  ADD COLUMN IF NOT EXISTS selfie_url VARCHAR(500) NULL AFTER id_number,
  ADD COLUMN IF NOT EXISTS approval_status ENUM('pending', 'approved', 'rejected') NOT NULL DEFAULT 'pending' AFTER id_document_url,
  ADD COLUMN IF NOT EXISTS approved_by INT NULL AFTER approval_status,
  ADD COLUMN IF NOT EXISTS approved_at DATETIME NULL AFTER approved_by,
  ADD COLUMN IF NOT EXISTS rejection_reason VARCHAR(500) NULL AFTER approved_at;

CREATE INDEX IF NOT EXISTS idx_riders_approval_status ON riders (approval_status);

ALTER TABLE riders
  ADD CONSTRAINT fk_riders_approved_by_user
  FOREIGN KEY (approved_by) REFERENCES users(user_id)
  ON DELETE SET NULL;
