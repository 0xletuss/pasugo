# Pasugo Backend Setup Guide - Windows

## Prerequisites

### 1. Install Python 3.12
Download and install from: https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe

**Installation Steps:**
- Run the installer
- **IMPORTANT**: Check ✓ "Add Python 3.12 to PATH"
- Click "Install Now"
- Restart your terminal/PowerShell after installation

**Verify Installation:**
```powershell
python --version
# Output should show: Python 3.12.10
```

---

## Backend Setup

### 2. Navigate to Project Directory
```powershell
cd "c:\Users\Earl Lawrence Banawa\Documents\Pasugo\pasugo"
```

### 3. Create Virtual Environment
```powershell
python -m venv venv
```

### 4. Activate Virtual Environment

**On Windows PowerShell:**
```powershell
.\venv\Scripts\Activate.ps1
```

**On Windows Command Prompt:**
```cmd
venv\Scripts\activate.bat
```

**On Windows Git Bash:**
```bash
source venv/Scripts/activate
```

You should see `(venv)` in your terminal prompt when activated.

### 5. Install Dependencies
```powershell
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### 6. Database Configuration

The database is already configured in `config.py` with these credentials:

```
Database: <your-db-name>
Host: <your-db-host>
Port: <your-db-port>
User: <your-db-user>
Password: <set-in-environment-variable>
```

**Verify Connection:**
```powershell
python test_connection.py
```

Expected output:
```
INFO:root:Testing database connection...
INFO:root:✅ Connection successful! Result: (1,)
INFO:root:Database is ready for use!
```

---

## Running the Backend Server

### 7. Start FastAPI Server

```powershell
# In project directory with venv activated
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### 8. Access API Documentation

Open in browser:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Testing Registration Endpoints

### Test Customer Registration

**Step 1: Request OTP**
```bash
curl -X POST "http://localhost:8000/api/auth/register/request-otp" \
  -H "Content-Type: application/json" \
  -d '{"email": "customer@test.com"}'
```

**Response:**
```json
{
  "success": true,
  "message": "OTP sent to email",
  "data": {
    "otp_code": "123456"
  }
}
```

**Step 2: Verify OTP & Register**
```bash
curl -X POST "http://localhost:8000/api/auth/register/verify-otp" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "customer@test.com",
    "otp": "123456",
    "full_name": "John Customer",
    "phone_number": "+639171234567",
    "password": "SecurePass123!",
    "user_type": "customer",
    "address": "123 Main St, Manila"
  }'
```

### Test Rider Registration

**Step 1: Request OTP**
```bash
curl -X POST "http://localhost:8000/api/auth/register/request-otp" \
  -H "Content-Type: application/json" \
  -d '{"email": "rider@test.com"}'
```

**Step 2: Verify OTP & Register as Rider**
```bash
curl -X POST "http://localhost:8000/api/auth/register/verify-otp" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "rider@test.com",
    "otp": "123456",
    "full_name": "Juan Rider",
    "phone_number": "+639271234567",
    "password": "SecurePass123!",
    "user_type": "rider",
    "address": "456 Rider Ave, Manila",
    "id_number": "123-456-789",
    "vehicle_type": "motorcycle",
    "vehicle_plate": "ABC-1234",
    "license_number": "DL-2026-001",
    "service_zones": "Makati, BGC, Taguig"
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "User registered successfully",
  "data": {
    "user_id": 1,
    "email": "rider@test.com",
    "full_name": "Juan Rider",
    "user_type": "rider",
    "rider_id": 1
  }
}
```

---

## Frontend Configuration

The frontend is already set up with separate registration pages:

- **Customer Registration**: `/www/pages/register.html`
- **Rider Registration**: `/www/pages/rider-register.html`

Both pages are properly separated with:
- Different form fields (rider page has vehicle/license info)
- Proper form validation
- Separate submission handlers
- Clear visual distinction

---

## Troubleshooting

### Issue: "Python was not found"

**Solution 1: Reinstall Python**
```powershell
winget uninstall Python.Python.3.12
winget install Python.Python.3.12 --accept-package-agreements
```

**Solution 2: Close and reopen terminal**
- The issue might be a PATH cache. Close all terminal windows and reopen.

**Solution 3: Use py launcher**
```powershell
py -3.12 --version
py -3.12 -m pip install -r requirements.txt
```

### Issue: "ModuleNotFoundError"

Make sure virtual environment is activated:
```powershell
# Check if (venv) appears in prompt
.\venv\Scripts\Activate.ps1
pip list  # Should show installed packages
```

### Issue: Database Connection Fails

**Check credentials in config.py:**
```python
DB_HOST: str = "<your-db-host>"
DB_PORT: int = 3306
DB_USER: str = "<your-db-user>"
DB_PASSWORD: str = "<set-via-env-var>"
DB_NAME: str = "<your-db-name>"
```

**Test connection:**
```powershell
python test_connection.py
```

---

## Development Workflow

1. **Terminal 1 - Backend Server:**
   ```powershell
   cd "c:\Users\Earl Lawrence Banawa\Documents\Pasugo\pasugo"
   .\venv\Scripts\Activate.ps1
   uvicorn app:app --reload
   ```

2. **Terminal 2 - Frontend Dev Server:**
   ```powershell
   cd "c:\Users\Earl Lawrence Banawa\Documents\frontnend\pasugoo"
   # If using Cordova:
   cordova serve
   # Or open in browser:
   # file:///.../www/index.html
   ```

3. **File Changes:**
   - Backend changes auto-reload with `--reload`
   - Frontend changes require manual refresh (Ctrl+R)

---

## Next Steps

1. ✅ Database is configured and tested
2. ✅ Customer registration page is ready
3. ✅ Rider registration page is ready and separate
4. ⏳ Run the backend server and test registration flow
5. ⏳ Test frontend registration with backend

---

## Quick Reference

| Component | Location | Status |
|-----------|----------|--------|
| Backend | `c:\Users\Earl Lawrence Banawa\Documents\Pasugo\pasugo` | ✅ Ready |
| Frontend | `c:\Users\Earl Lawrence Banawa\Documents\frontnend\pasugoo` | ✅ Ready |
| Database | Aiven Cloud (defaultdb) | ✅ Configured |
| Customer Registration | `/www/pages/register.html` | ✅ Separate |
| Rider Registration | `/www/pages/rider-register.html` | ✅ Separate |
| Auth API | `/api/auth/*` | ✅ Ready |
