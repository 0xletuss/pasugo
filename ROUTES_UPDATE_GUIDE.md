# Field Name Mapping Guide - Routes Update

Use this guide to update your route handlers to match the new model field names.

## Rider Routes (`routes/riders.py`)

### Old → New Field Mapping

| Old Field Name | New Field Name | Type | Notes |
|---|---|---|---|
| `status` | `availability_status` | Enum | Must use new enum values |
| `vehicle_plate` | `license_plate` | String | Database column renamed |
| `license_number` | `id_number` | String | Database column renamed |
| `total_deliveries` | `total_tasks_completed` | Integer | Tracks completed tasks |
| `is_verified` | *(removed)* | - | No longer used |
| `current_location_lat` | *(removed)* | - | GPS tracking removed |
| `current_location_lng` | *(removed)* | - | GPS tracking removed |
| *(new)* | `total_earnings` | Decimal | New field for earnings tracking |
| *(new)* | `id_number` | String | Unique identifier (PK for driver ID) |

### RiderStatus Enum Values

**Updated enum - use these exact values:**
```python
class RiderStatus(str, enum.Enum):
    available = "available"      # Rider is online and available
    busy = "busy"                # Rider is currently on a task
    offline = "offline"          # Rider is logged out
    suspended = "suspended"      # NEW - Rider account suspended
```

### Code Update Example

**BEFORE:**
```python
@app.post("/riders")
def create_rider(rider_data):
    rider = Rider(
        status="available",
        vehicle_plate="ABC-1234",
        license_number="DL-12345",
        total_deliveries=0
    )
    return rider

@app.get("/riders/{rider_id}")
def get_rider(rider_id: int):
    rider = db.query(Rider).filter(Rider.rider_id == rider_id).first()
    return {
        "status": rider.status,
        "vehicle_plate": rider.vehicle_plate,
        "license_number": rider.license_number,
        "total_deliveries": rider.total_deliveries
    }
```

**AFTER:**
```python
@app.post("/riders")
def create_rider(rider_data):
    rider = Rider(
        availability_status="available",
        license_plate="ABC-1234",
        id_number="DL-12345",
        total_tasks_completed=0,
        total_earnings=Decimal("0.00")  # NEW field
    )
    return rider

@app.get("/riders/{rider_id}")
def get_rider(rider_id: int):
    rider = db.query(Rider).filter(Rider.rider_id == rider_id).first()
    return {
        "availability_status": rider.availability_status,
        "license_plate": rider.license_plate,
        "id_number": rider.id_number,
        "total_tasks_completed": rider.total_tasks_completed,
        "total_earnings": float(rider.total_earnings)  # NEW field
    }
```

---

## Payment Routes (`routes/payments.py`)

### Old → New Field Mapping

| Old Field Name | New Field Name | Type | Notes |
|---|---|---|---|
| `amount` | `bill_amount` + `service_fee` + `total_collected` | Decimal | Split into 3 fields |
| `payment_proof_path` | *(removed)* | - | Use gcash_receipt_path instead |
| `transaction_reference` | `gcash_reference_number` | String | For GCash payments only |
| *(new)* | `rider_id` | Integer | FK - Required field |
| *(new)* | `bill_amount` | Decimal | Bill payment amount |
| *(new)* | `service_fee` | Decimal | Service charge |
| *(new)* | `total_collected` | Decimal | Total amount collected |
| *(new)* | `gcash_receipt_path` | String | Path to GCash receipt image |
| *(new)* | `payment_date` | DateTime | When payment was made |
| *(removed)* | `completed_at` | - | Use payment_date instead |
| *(removed)* | `updated_at` | - | Only created_at now |

### PaymentStatus Enum Values

**Updated enum - use these exact values:**
```python
class PaymentStatus(str, enum.Enum):
    pending = "pending"          # Awaiting verification
    verified = "verified"        # Payment verified by rider
    completed = "completed"      # Payment processed
    failed = "failed"            # Payment failed
```

### Code Update Example

**BEFORE:**
```python
@app.post("/payments")
def create_payment(payment_data):
    payment = Payment(
        request_id=payment_data.request_id,
        customer_id=payment_data.customer_id,
        amount=100.00,  # Single amount field
        payment_status="pending",
        transaction_reference="GC123456" if payment_data.method == "gcash" else None,
        payment_proof_path="/uploads/proof.jpg"
    )
    return payment
```

**AFTER:**
```python
@app.post("/payments")
def create_payment(payment_data):
    # Must include rider_id and split the amount
    payment = Payment(
        request_id=payment_data.request_id,
        customer_id=payment_data.customer_id,
        rider_id=payment_data.rider_id,  # NEW - Required
        bill_amount=Decimal("95.00"),    # Split amount
        service_fee=Decimal("5.00"),     # Split amount
        total_collected=Decimal("100.00"),  # Split amount
        payment_method=payment_data.method,
        payment_status="pending",
        payment_date=datetime.now(),     # NEW - Required
        gcash_reference_number="GC123456" if payment_data.method == "gcash" else None,
        gcash_receipt_path="/uploads/receipt.jpg" if payment_data.method == "gcash" else None
    )
    return payment
```

---

## Rating Routes (`routes/ratings.py` or `routes/complaints.py`)

### Old → New Field Mapping

| Old Field Name | New Field Name | Type | Notes |
|---|---|---|---|
| `rating_score` | `overall_rating` | Decimal(2,1) | Renamed field |
| `review_comment` | *(removed)* | - | No longer used |
| *(new)* | `task_id` | Integer | FK - References rider_tasks |
| *(new)* | `is_anonymous` | Boolean | Anonymous rating option |
| *(new)* | `rating_date` | DateTime | When rating was submitted |
| `customer_id` | `customer_id` | Integer | Now properly stored |

### Code Update Example

**BEFORE:**
```python
@app.post("/ratings")
def create_rating(rating_data):
    rating = Rating(
        request_id=rating_data.request_id,
        rider_id=rating_data.rider_id,
        customer_id=rating_data.customer_id,
        rating_score=4.5,  # OLD field
        review_comment="Great service!",  # Removed
        created_at=datetime.now()
    )
    return rating
```

**AFTER:**
```python
@app.post("/ratings")
def create_rating(rating_data):
    rating = Rating(
        request_id=rating_data.request_id,
        rider_id=rating_data.rider_id,
        customer_id=rating_data.customer_id,
        task_id=rating_data.task_id,  # NEW - Required
        overall_rating=Decimal("4.5"),  # RENAMED field
        is_anonymous=rating_data.is_anonymous if hasattr(rating_data, 'is_anonymous') else False,  # NEW
        rating_date=datetime.now()  # NEW - Required
    )
    return rating
```

---

## New Models - New Routes Needed

### RiderTask Routes (`routes/rider_tasks.py` - NEW)

```python
# Create task when bill request is assigned to rider
@app.post("/tasks")
def create_task(task_data):
    task = RiderTask(
        request_id=task_data.request_id,
        rider_id=task_data.rider_id,
        task_type="collect_payment",  # or "pay_bill", "deliver_receipt"
        task_status="pending",
        assigned_at=datetime.now()
    )
    return task

# Get tasks for a specific rider
@app.get("/riders/{rider_id}/tasks")
def get_rider_tasks(rider_id: int):
    tasks = db.query(RiderTask).filter(RiderTask.rider_id == rider_id).all()
    return tasks

# Update task status
@app.patch("/tasks/{task_id}")
def update_task(task_id: int, status: str):
    task = db.query(RiderTask).filter(RiderTask.task_id == task_id).first()
    task.task_status = status  # pending, accepted, in_progress, completed, failed
    if status == "accepted":
        task.accepted_at = datetime.now()
    elif status == "in_progress":
        task.started_at = datetime.now()
    elif status == "completed":
        task.completed_at = datetime.now()
    return task
```

### PasswordResetToken Routes (in `routes/auth.py`)

```python
# Request password reset
@app.post("/auth/password-reset/request")
def request_password_reset(email: str):
    user = db.query(User).filter(User.email == email).first()
    token = PasswordResetToken(
        user_id=user.user_id,
        reset_token=generate_secure_token(),
        expires_at=datetime.now() + timedelta(hours=1)
    )
    db.add(token)
    db.commit()
    # Send email with token
    return {"message": "Reset link sent to email"}

# Verify and reset password
@app.post("/auth/password-reset/verify")
def verify_reset_token(token: str, new_password: str):
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.reset_token == token,
        PasswordResetToken.is_used == False,
        PasswordResetToken.expires_at > datetime.now()
    ).first()
    
    if not reset_token:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    user = db.query(User).filter(User.user_id == reset_token.user_id).first()
    user.password_hash = hash_password(new_password)
    reset_token.is_used = True
    reset_token.used_at = datetime.now()
    db.commit()
    return {"message": "Password reset successful"}
```

---

## Summary of Changes

### Fields to Remove from Route Responses
- `status` → use `availability_status`
- `vehicle_plate` → use `license_plate`
- `license_number` → use `id_number`
- `total_deliveries` → use `total_tasks_completed`
- `is_verified` (riders)
- `current_location_lat/lng`
- `payment_proof_path`
- `transaction_reference`
- `review_comment`

### Fields to Add to Route Responses
- `suspended` status (riders)
- `total_earnings` (riders)
- `rider_id` (payments - REQUIRED)
- `bill_amount`, `service_fee`, `total_collected` (payments - split from amount)
- `gcash_reference_number`, `gcash_receipt_path` (payments)
- `payment_date` (payments - REQUIRED)
- `task_id` (ratings - REQUIRED)
- `is_anonymous`, `rating_date` (ratings - NEW)

### New Tables/Routes to Implement
- `RiderTask` - Track individual delivery/payment tasks
- `PasswordResetToken` - Secure password recovery

---

**Last Updated:** February 3, 2026
**Status:** All critical models fixed and aligned with database schema
