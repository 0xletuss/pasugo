# Model Fixes - Verification Checklist

## ✅ Critical Fixes Completed

### Priority 1: Database Alignment

- [x] **Rider Model** (`models/rider.py`)
  - [x] Renamed `vehicle_plate` → `license_plate`
  - [x] Renamed `license_number` → `id_number` with UNIQUE constraint
  - [x] Renamed `status` → `availability_status`
  - [x] Added `suspended` to RiderStatus enum
  - [x] Removed `current_location_lat`, `current_location_lng`
  - [x] Removed `is_verified`
  - [x] Removed `updated_at`
  - [x] Renamed `total_deliveries` → `total_tasks_completed`
  - [x] Added `total_earnings` (DECIMAL(10,2))
  - [x] Added relationship: `tasks` → RiderTask

- [x] **Payment Model** (`models/payment.py`)
  - [x] Updated PaymentStatus enum (removed processing, refunded)
  - [x] Added `rider_id` (ForeignKey, NOT NULL)
  - [x] Split `amount` into `bill_amount`, `service_fee`, `total_collected`
  - [x] Renamed `transaction_reference` → `gcash_reference_number`
  - [x] Renamed `payment_proof_path` → `gcash_receipt_path`
  - [x] Added `payment_date` (DateTime, NOT NULL)
  - [x] Removed UNIQUE constraint on `request_id`
  - [x] Removed `completed_at`, `updated_at`
  - [x] Added relationships: `customer`, `rider`

- [x] **Rating Model** (`models/rating.py`)
  - [x] Changed `__tablename__` from "ratings" → "rider_ratings"
  - [x] Added `task_id` (ForeignKey to rider_tasks, NOT NULL)
  - [x] Renamed `rating_score` → `overall_rating` (DECIMAL(2,1))
  - [x] Removed `review_comment`
  - [x] Added `is_anonymous` (BOOLEAN, default=False)
  - [x] Added `rating_date` (DateTime, NOT NULL)
  - [x] Added `customer_id` (ForeignKey, indexed)
  - [x] Removed UNIQUE constraint on `request_id`
  - [x] Added relationships: `customer`

- [x] **OTP Model** (`models/otp.py`)
  - [x] Verified - No changes needed
  - [x] Table exists in database ✅
  - [x] All fields match schema ✅
  - [x] Ready for use ✅

### Priority 2: New Models Created

- [x] **RiderTask Model** (`models/rider_task.py`)
  - [x] Created new model for rider_tasks table
  - [x] All fields implemented correctly
  - [x] Relationships configured
  - [x] Enums defined (TaskType, TaskStatus)

- [x] **PasswordResetToken Model** (`models/password_reset_token.py`)
  - [x] Created new model for password_reset_tokens table
  - [x] All fields implemented correctly
  - [x] Relationships configured

### Relationship Updates

- [x] **User Model** (`models/user.py`)
  - [x] Added: `payments` relationship
  - [x] Added: `ratings_given` relationship
  - [x] Added: `password_reset_tokens` relationship

- [x] **Rider Model** (`models/rider.py`)
  - [x] Added: `tasks` relationship to RiderTask

- [x] **BillRequest Model** (`models/bill_request.py`)
  - [x] Added: `rider_tasks` relationship

---

## 📋 Implementation Checklist

### Step 1: Update Route Handlers
- [ ] Update `routes/riders.py` to use new field names
  - [ ] `status` → `availability_status`
  - [ ] `vehicle_plate` → `license_plate`
  - [ ] `license_number` → `id_number`
  - [ ] `total_deliveries` → `total_tasks_completed`
  - [ ] Handle new `total_earnings` field
  
- [ ] Update `routes/payments.py` to use new fields
  - [ ] Add `rider_id` parameter (required)
  - [ ] Split `amount` into three fields
  - [ ] Use `gcash_reference_number` for GCash
  - [ ] Use `gcash_receipt_path` for receipts
  - [ ] Add `payment_date` parameter

- [ ] Update `routes/complaints.py` or ratings endpoints
  - [ ] `rating_score` → `overall_rating`
  - [ ] Add `task_id` parameter
  - [ ] Add `is_anonymous` parameter
  - [ ] Add `rating_date` parameter
  - [ ] Remove `review_comment` handling

- [ ] Create `routes/rider_tasks.py` (NEW)
  - [ ] POST /tasks - Create task
  - [ ] GET /tasks - List all tasks
  - [ ] GET /tasks/{task_id} - Get single task
  - [ ] PATCH /tasks/{task_id} - Update task status
  - [ ] GET /riders/{rider_id}/tasks - Rider's tasks

- [ ] Update `routes/auth.py` for password reset
  - [ ] POST /auth/password-reset/request
  - [ ] POST /auth/password-reset/verify

### Step 2: Update Pydantic Schemas
- [ ] Update `schemas/rider.py`
  - [ ] Use `availability_status` in requests/responses
  - [ ] Use `id_number`, `license_plate` in requests
  - [ ] Include `total_earnings` in responses

- [ ] Update `schemas/payment.py`
  - [ ] Add `rider_id` to PaymentCreate schema
  - [ ] Add `bill_amount`, `service_fee`, `total_collected`
  - [ ] Add `payment_date` parameter
  - [ ] Add `gcash_reference_number`, `gcash_receipt_path`

- [ ] Update `schemas/rating.py`
  - [ ] Use `overall_rating` instead of `rating_score`
  - [ ] Add `task_id` parameter
  - [ ] Add `is_anonymous` parameter
  - [ ] Add `rating_date` parameter

- [ ] Create new schemas for RiderTask and PasswordResetToken

### Step 3: Update Database/Migrations
- [ ] Generate Alembic migration (if using)
  ```bash
  alembic revision --autogenerate -m "Update models to match database schema"
  ```
- [ ] Review migration file for accuracy
- [ ] Run migration:
  ```bash
  alembic upgrade head
  ```

### Step 4: Testing
- [ ] Test Rider endpoints
  - [ ] Create rider with new fields
  - [ ] Update rider status
  - [ ] Verify field names in responses
  
- [ ] Test Payment endpoints
  - [ ] Create payment with all required fields
  - [ ] Verify payment_date is set correctly
  - [ ] Test GCash fields

- [ ] Test Rating endpoints
  - [ ] Create rating with task_id
  - [ ] Test is_anonymous flag
  - [ ] Verify overall_rating field

- [ ] Test new RiderTask endpoints
  - [ ] Create task
  - [ ] Update task status
  - [ ] List tasks by rider

- [ ] Test PasswordResetToken flow
  - [ ] Request password reset
  - [ ] Verify token
  - [ ] Reset password

### Step 5: Documentation
- [ ] Update API documentation
- [ ] Update request/response examples
- [ ] Update field descriptions
- [ ] Update error messages

### Step 6: Deployment
- [ ] Backup current database
- [ ] Deploy code changes
- [ ] Run migrations on production
- [ ] Verify all endpoints work
- [ ] Monitor logs for errors

---

## 🔍 Database Schema Verification

Run these queries to verify database alignment:

```sql
-- Verify Riders table
DESCRIBE riders;
-- Should show: id_number, license_plate, availability_status, total_tasks_completed, total_earnings

-- Verify Payments table  
DESCRIBE payments;
-- Should show: rider_id, bill_amount, service_fee, total_collected, payment_date, gcash_reference_number, gcash_receipt_path

-- Verify Rider Ratings table
DESCRIBE rider_ratings;
-- Should show: task_id, overall_rating, is_anonymous, rating_date

-- Verify OTPs table
DESCRIBE otps;
-- Should already exist and be correct

-- Verify RiderTasks table
DESCRIBE rider_tasks;
-- Should exist with task_type, task_status

-- Verify Password Reset Tokens table
DESCRIBE password_reset_tokens;
-- Should exist with reset_token, is_used, expires_at
```

---

## 📊 Status Summary

| Component | Status | Critical | Notes |
|-----------|--------|----------|-------|
| Rider Model | ✅ FIXED | YES | 7 field changes |
| Payment Model | ✅ FIXED | YES | 7 new fields added |
| Rating Model | ✅ FIXED | YES | Table name changed |
| OTP Model | ✅ VERIFIED | YES | No changes needed |
| RiderTask Model | ✅ NEW | NO | Optional enhancement |
| PasswordResetToken | ✅ NEW | NO | Optional enhancement |
| Relationships | ✅ UPDATED | - | All models linked |
| Route Updates | ⏳ TODO | YES | In progress |
| Schema Updates | ⏳ TODO | YES | Pending |
| Database Migration | ⏳ TODO | YES | Pending |
| Testing | ⏳ TODO | YES | Pending |

---

## 📞 Support

### Common Issues & Solutions

**Issue:** `Table 'rider_ratings' not found`
- **Solution:** Run database migration: `alembic upgrade head`

**Issue:** Field name errors in routes
- **Solution:** Use field mapping guide in ROUTES_UPDATE_GUIDE.md

**Issue:** Missing ForeignKey relationship**
- **Solution:** Verify `rider_id` is included in Payment creation

**Issue:** Decimal arithmetic issues**
- **Solution:** Use `from decimal import Decimal` and convert properly

---

**Last Updated:** February 3, 2026
**Completion Status:** Models 100% Fixed | Routes Update In Progress
