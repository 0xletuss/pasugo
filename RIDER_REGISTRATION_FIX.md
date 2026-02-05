# Rider Registration Fix - Documentation

## Problem Statement

The registration endpoint was failing with `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 1214: invalid start byte` when attempting to register as a rider with an ID file upload.

### Root Cause

- Frontend was sending multipart FormData to `/api/auth/register`
- Backend `/api/auth/register` endpoint only accepts JSON
- FastAPI's validation layer was failing to parse the binary file data as JSON
- When FastAPI tried to create an error response, it attempted to encode the binary file data as UTF-8, which failed

## Solution Overview

Created a new dedicated endpoint for rider registration that:

1. Accepts multipart FormData (with mixed text and file fields)
2. Creates both User and Rider records in one request
3. Handles file uploads to Cloudinary
4. Stores Cloudinary URL in rider profile

## Changes Made

### 1. Backend Changes

#### A. New Endpoint: `/api/riders/register`

**File:** `routes/riders.py`

**Method:** POST

**Request Format:** multipart/form-data

**Request Parameters:**

```
User Registration Fields:
- full_name (string, required) - 2-100 characters
- email (string, required) - Valid email
- phone_number (string, required) - 9-15 digits
- password (string, required) - Min 8 characters
- address (string, required)

Rider-Specific Fields:
- id_number (string, required) - National ID / Identification number
- vehicle_type (string, required) - e.g., "motorcycle", "car", "bicycle"
- vehicle_plate (string, required) - Vehicle plate number
- license_number (string, required) - Driver's license number
- service_zones (string, optional) - Comma-separated service areas

File Upload:
- id_file (file, optional) - ID document (image)
```

**Response on Success (201):**

```json
{
  "success": true,
  "message": "Rider registered successfully",
  "data": {
    "user_id": 123,
    "rider_id": 456,
    "email": "rider@example.com",
    "full_name": "John Doe",
    "phone_number": "09123456789",
    "vehicle_type": "motorcycle",
    "id_document_url": "https://res.cloudinary.com/.../pasugo/riders/123/id_document.jpg",
    "user_type": "rider"
  }
}
```

**Response on Error (400/500):**

```json
{
  "detail": "Error message describing what went wrong"
}
```

#### B. Database Model Update: `models/rider.py`

Added new column to Rider model:

```python
license_number = Column(String(50), nullable=True)  # Driver's license number
```

Also renamed field in code from `license_plate` → `vehicle_plate` for clarity.

#### C. Database Migration: `migrations/002_add_license_number_to_riders.sql`

```sql
ALTER TABLE riders
ADD COLUMN license_number VARCHAR(50) DEFAULT NULL AFTER license_plate,
ADD INDEX idx_license_number (license_number);
```

### 2. Frontend Changes

#### A. HTML Form Update: `www/pages/register.html`

Added new ID Number field for riders:

```html
<div class="form-group">
  <input
    type="text"
    id="idNumber"
    name="idNumber"
    placeholder="National ID / ID Number"
  />
</div>
```

#### B. Form Submission Update: `www/js/auth.js`

Updated `RegistrationForm` class:

1. **`getFormData()` method** - Now includes `id_number` field:

```javascript
if (this.userType === "rider") {
  data.id_number = document.getElementById("idNumber")?.value.trim() || null;
  // ... other rider fields
}
```

2. **`submitRegistration()` method** - Routes to correct endpoint:

```javascript
// If rider registration, use /api/riders/register
if (data.user_type === "rider" || data.id_file) {
  endpoint = `${API_BASE_URL_AUTH}/api/riders/register`;
  // Build FormData with all fields
}
```

3. **`validateField()` method** - Added validation for ID number:

```javascript
case "idNumber":
  if (this.userType === "rider" && !value) {
    errorMessage = "ID number is required";
  } else if (value && value.length < 5) {
    errorMessage = "ID number must be at least 5 characters";
  }
  break;
```

## Installation & Testing Steps

### 1. Apply Database Migration

Run the migration script on your database:

```bash
mysql -h your_host -u your_user -p your_database < migrations/002_add_license_number_to_riders.sql
```

Or if using Render:

```bash
# Run via Render PostgreSQL console
```

### 2. Restart Backend

```bash
# If running locally
python app.py

# If on Render
git push origin main  # This triggers automatic redeploy
```

### 3. Test Rider Registration with File Upload

**Test Case 1: Rider Registration with File**

```bash
curl -X POST http://localhost:8000/api/riders/register \
  -F "full_name=John Rider" \
  -F "email=john@example.com" \
  -F "phone_number=09123456789" \
  -F "password=SecurePass123!" \
  -F "address=Manila" \
  -F "id_number=123456789" \
  -F "vehicle_type=motorcycle" \
  -F "vehicle_plate=ABC1234" \
  -F "license_number=DL123456789" \
  -F "service_zones=Manila,Makati" \
  -F "id_file=@/path/to/id_photo.jpg"
```

**Test Case 2: Rider Registration without File**

```bash
curl -X POST http://localhost:8000/api/riders/register \
  -F "full_name=Jane Rider" \
  -F "email=jane@example.com" \
  -F "phone_number=09198765432" \
  -F "password=SecurePass123!" \
  -F "address=Cebu" \
  -F "id_number=987654321" \
  -F "vehicle_type=bicycle" \
  -F "vehicle_plate=XYZ9876" \
  -F "license_number=DL987654321" \
  -F "service_zones=Cebu"
```

**Test Case 3: Customer Registration (Unchanged)**

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Customer",
    "email": "customer@example.com",
    "phone_number": "09111111111",
    "password": "SecurePass123!",
    "user_type": "customer",
    "address": "Quezon City"
  }'
```

### 4. Frontend Testing

1. Navigate to registration page
2. Select "Rider" from "Register as" dropdown
3. Fill in all fields including ID Number
4. Optionally upload ID file
5. Click "Sign Up"
6. Should succeed with redirected to login

### 5. Verify in Database

```sql
-- Check if rider was created
SELECT r.*, u.full_name, u.email
FROM riders r
JOIN users u ON r.user_id = u.user_id
WHERE u.email = 'john@example.com';

-- Expected output:
-- - rider_id: Should be auto-incremented
-- - user_id: Foreign key to users table
-- - id_number: "123456789"
-- - id_document_url: Cloudinary URL if file was uploaded
-- - vehicle_type: "motorcycle"
-- - vehicle_plate: "ABC1234"
-- - license_number: "DL123456789"
```

## Error Handling

The new endpoint handles:

1. **Duplicate Email/Phone** - Returns 400 with "Email already registered" or similar
2. **Duplicate ID Number** - Returns 400 with "ID number already registered"
3. **Invalid Input** - Returns 400 with detailed validation error
4. **File Upload Failure** - Returns 500 with details about upload error
5. **Database Errors** - Rolls back transaction and returns 500 error

## Backward Compatibility

- Original `/api/auth/register` endpoint remains unchanged
- Customer registration flow is unaffected
- Existing rider profile creation at `/api/riders/profile` still works
- All other authentication endpoints unchanged

## Security Considerations

1. **File Validation**: Cloudinary handles virus scanning
2. **File Size Limits**: Set via Cloudinary settings
3. **CORS**: Ensure CORS policy allows rider registration route
4. **Rate Limiting**: Consider adding rate limiting to prevent abuse
5. **Input Validation**: All inputs validated before processing
6. **Password Hashing**: Passwords hashed with bcrypt before storage

## Future Enhancements

1. Add ID number verification/validation
2. Implement automatic license verification API integration
3. Add document verification workflow (admin approval)
4. Support multiple document uploads (license, registration, etc.)
5. Add SMS verification for phone numbers
6. Implement KYC (Know Your Customer) checks

## Troubleshooting

### Error: "UnicodeDecodeError" still occurs

- Ensure `/api/riders/register` is being called, not `/api/auth/register`
- Check that Content-Type is not explicitly set to application/json
- Verify FormData is being used when file is present

### Error: "Cloudinary upload failed"

- Verify CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET are set
- Check file size limits
- Verify file format is supported (JPG, PNG, etc.)

### Error: "Database migration failed"

- Ensure database user has ALTER TABLE permissions
- Check that column doesn't already exist
- Verify MySQL/PostgreSQL syntax is correct

### File not appearing in Cloudinary

- Check Cloudinary console for upload attempts
- Verify folder path is correct
- Check API credentials configuration

## File Changes Summary

**Modified Files:**

- `routes/riders.py` - Added /api/riders/register endpoint
- `models/rider.py` - Added license_number column
- `www/pages/register.html` - Added ID Number field
- `www/js/auth.js` - Updated form handling and submission logic

**New Files:**

- `migrations/002_add_license_number_to_riders.sql` - Database migration

**Unchanged Files:**

- `routes/auth.py` - Original /api/auth/register endpoint unchanged
- `config.py` - Cloudinary config unchanged
- All other files remain unchanged
