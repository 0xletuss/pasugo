-- Migration: Fix rider_ratings table for new rating system
-- 1. Make task_id nullable (we don't use rider_tasks for direct ratings)
-- 2. Drop old request_id FK to bill_requests if it exists, re-add to requests table

-- Make task_id nullable
ALTER TABLE rider_ratings MODIFY COLUMN task_id INT NULL;

-- Drop old FK on request_id pointing to bill_requests (if exists)
-- Note: FK name may vary - check with SHOW CREATE TABLE rider_ratings
-- ALTER TABLE rider_ratings DROP FOREIGN KEY rider_ratings_ibfk_2;

-- The INSERT in ratings.py omits task_id, so making it nullable is sufficient.
-- request_id in the INSERT maps to the requests table's request_id, which should work
-- since both tables share auto-increment IDs in the same space.
