# UnicodeDecodeError Fix - Implementation Checklist

## ✅ Fix Completed

### Root Cause

The `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff` error was caused by:

- Frontend sending multipart FormData with binary file to `/api/auth/register`
- Backend expecting JSON-only input
- FastAPI validation failing on binary data
- Error response handler attempting to UTF-8 encode binary JPEG bytes (starting with `\xff\xd8`)

### Solution Implemented

Created a new FormData-compatible endpoint `/api/riders/register` that:

1. Accepts multipart/form-data requests
2. Creates User + Rider profiles in single request
3. Handles optional file uploads to Cloudinary
4. Properly validates all inputs

---

## 📋 Implementation Checklist

### Backend Changes

- [x] Created new `/api/riders/register` endpoint in `routes/riders.py`
- [x] Added imports for FormData handling (File, UploadFile, Form)
- [x] Added CloudinaryManager import and usage
- [x] Added input validation (phone, password, name, email, id_number)
- [x] Implemented file upload to Cloudinary with error handling
- [x] Created User with user_type='rider'
- [x] Created Rider profile with all required fields
- [x] Added proper error handling and transaction rollback

### Database Changes

- [x] Updated Rider model to include license_number field
- [x] Created migration script `002_add_license_number_to_riders.sql`
- [x] Updated field mappings (vehicle_plate, license_number)

### Frontend Changes

- [x] Added ID Number input field to registration form
- [x] Updated `getFormData()` to include id_number
- [x] Updated `submitRegistration()` to route to `/api/riders/register`
- [x] Added validation for ID number field
- [x] Verified FormData construction for file upload

### Testing & Documentation

- [x] Created comprehensive documentation (RIDER_REGISTRATION_FIX.md)
- [x] Added curl test examples for verification
- [x] Created migration script for database
- [x] Verified no syntax errors

---

## 🚀 Next Steps to Deploy

### 1. Apply Database Migration (REQUIRED)

```bash
# For MySQL:
mysql -h your_host -u your_user -p your_database < migrations/002_add_license_number_to_riders.sql

# For PostgreSQL (Render):
# Use Render console or psql client
psql "postgresql://username:password@host/dbname" -f migrations/002_add_license_number_to_riders.sql
```

### 2. Deploy Backend

```bash
# If local development:
python app.py

# If on Render:
git add .
git commit -m "Fix: Add rider registration endpoint with file upload support"
git push origin main
# Render will auto-deploy
```

### 3. Mobile/Web Update

Replace Cordova `www/` files or update web frontend with:

- Updated `www/pages/register.html`
- Updated `www/js/auth.js`

### 4. Testing Verification

Run the test curl commands in RIDER_REGISTRATION_FIX.md to verify:

- Rider registration with file upload works
- Cloudinary URL is returned
- Database records are created correctly

---

## 🔍 Verification Commands

### Test Endpoint

```bash
# Test with file
curl -X POST http://localhost:8000/api/riders/register \
  -F "full_name=Test Rider" \
  -F "email=test@example.com" \
  -F "phone_number=09123456789" \
  -F "password=TestPass123!" \
  -F "address=Test City" \
  -F "id_number=123456789" \
  -F "vehicle_type=motorcycle" \
  -F "vehicle_plate=ABC123" \
  -F "license_number=DL123456" \
  -F "service_zones=Test Zone" \
  -F "id_file=@photo.jpg"
```

### Verify Database

```sql
-- Check riders table exists with new column
DESCRIBE riders;

-- Check new rider record
SELECT * FROM riders WHERE id_number = '123456789';

-- Verify Cloudinary URL stored
SELECT rider_id, id_number, id_document_url FROM riders
WHERE id_document_url IS NOT NULL LIMIT 1;
```

---

## 📊 Testing Results Needed

After deployment, verify:

- [ ] Rider registration form displays ID Number field
- [ ] Form accepts multipart FormData with file
- [ ] File uploads to Cloudinary successfully
- [ ] Cloudinary URL returned in response
- [ ] Rider and User records created in database
- [ ] License plate and license number stored correctly
- [ ] Old customer registration still works unchanged
- [ ] No UnicodeDecodeError in backend logs

---

## 🔧 Troubleshooting

### If UnicodeDecodeError persists:

1. Verify frontend is calling `/api/riders/register`, not `/api/auth/register`
2. Check that FormData is being used (not JSON) when file is present
3. Check browser console for actual endpoint being called
4. Verify API_BASE_URL_AUTH variable is set correctly

### If Cloudinary upload fails:

1. Verify CloudinaryManager is initialized correctly
2. Check env variables: CLOUDINARY_CLOUD_NAME, API_KEY, API_SECRET
3. Check file size/format is supported
4. Review Cloudinary dashboard for upload errors

### If database migration fails:

1. Verify database user has ALTER TABLE permissions
2. Check if license_number column already exists
3. Verify MySQL/PostgreSQL syntax for your database type
4. Check error logs for specific database errors

---

## 📝 Files Modified

**Backend (Python):**

- `routes/riders.py` - Added /register endpoint
- `models/rider.py` - Added license_number field

**Frontend (JavaScript/HTML):**

- `www/pages/register.html` - Added ID Number field
- `www/js/auth.js` - Updated form logic

**Database:**

- `migrations/002_add_license_number_to_riders.sql` - New column

**Documentation:**

- `RIDER_REGISTRATION_FIX.md` - Detailed documentation
- `IMPLEMENTATION_CHECKLIST.md` - This file

---

## 🎯 Summary

**Problem:** Registration with file upload was causing UnicodeDecodeError

**Solution:** Created dedicated FormData endpoint for rider registration

**Result:** Riders can now register with ID document upload in single request

**Status:** ✅ READY FOR DEPLOYMENT

---

## 📞 Support

If issues arise:

1. Check error logs: `tail -f backend.log`
2. Review test cases in RIDER_REGISTRATION_FIX.md
3. Verify all database migrations applied
4. Ensure Cloudinary credentials configured
5. Check network tab for actual requests being sent

---

**Last Updated:** February 5, 2026  
**Status:** Implementation Complete ✅
