# Pasugo Backend API

A FastAPI-based backend for the Pasugo bill payment and delivery service platform.

## Features

- 🔐 JWT Authentication & Authorization
- 👥 User Management (Customer, Rider, Admin)
- 📝 Bill Payment Requests
- 🚴 Rider Management & Assignment
- 💳 Payment Processing
- 📢 Notifications System
- ⭐ Ratings & Reviews
- 🎫 Complaints Management

## Tech Stack

- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - SQL ORM
- **MySQL** - Database
- **PyMySQL** - MySQL driver
- **JWT** - Authentication
- **Pydantic** - Data validation

## Project Structure

```
pasugo-backend/
├── app.py                 # Main application entry point
├── config.py              # Configuration settings
├── database.py            # Database connection setup
├── models/                # SQLAlchemy models
│   ├── __init__.py
│   ├── user.py
│   ├── rider.py
│   ├── bill_request.py
│   ├── complaint.py
│   ├── payment.py
│   ├── notification.py
│   └── ...
├── routes/                # API route handlers
│   ├── __init__.py
│   ├── auth.py
│   ├── users.py
│   ├── bill_requests.py
│   ├── riders.py
│   ├── complaints.py
│   ├── notifications.py
│   └── payments.py
├── utils/                 # Utility functions
│   ├── __init__.py
│   ├── security.py        # Password hashing, JWT
│   ├── dependencies.py    # Auth dependencies
│   └── responses.py       # Standard responses
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
└── README.md             # This file
```

## Setup Instructions

### 1. Clone the repository

```bash
git clone <repository-url>
cd pasugo-backend
```

### 2. Create virtual environment

```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` file with your configuration:
- Update `SECRET_KEY` with a secure random string (min 32 characters)
- Verify database credentials
- Adjust other settings as needed

### 5. Run the application

```bash
# Development mode (with auto-reload)
python app.py

# Or using uvicorn directly
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Documentation**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout

### Users
- `GET /users/me` - Get current user info
- `PUT /users/me` - Update current user
- `GET /users/{user_id}` - Get user by ID

### Bill Requests
- `POST /bill-requests` - Create bill request
- `GET /bill-requests/my-requests` - Get user's requests
- `GET /bill-requests/{request_id}` - Get request details
- `PATCH /bill-requests/{request_id}/cancel` - Cancel request

### Riders
- `POST /riders/profile` - Create rider profile
- `GET /riders/profile` - Get rider profile
- `PATCH /riders/location` - Update location
- `PATCH /riders/status` - Update status
- `GET /riders/available-requests` - Get available requests
- `POST /riders/accept-request/{request_id}` - Accept request

### Complaints
- `POST /complaints` - Create complaint
- `GET /complaints/my-complaints` - Get user's complaints
- `GET /complaints/{complaint_id}` - Get complaint details
- `POST /complaints/{complaint_id}/reply` - Add reply (admin)

### Notifications
- `GET /notifications` - Get notifications
- `GET /notifications/unread-count` - Get unread count
- `PATCH /notifications/{id}/read` - Mark as read
- `PATCH /notifications/mark-all-read` - Mark all as read

### Payments
- `POST /payments` - Create payment
- `GET /payments/my-payments` - Get user's payments
- `GET /payments/{payment_id}` - Get payment details

## Deployment to Render

### 1. Create a new Web Service on Render

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click "New +" → "Web Service"
3. Connect your Git repository

### 2. Configure the service

- **Name**: `pasugo-api`
- **Environment**: `Python 3`
- **Region**: Choose closest to your users
- **Branch**: `main` (or your default branch)
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`

### 3. Add Environment Variables

In the Render dashboard, add these environment variables:

```
SECRET_KEY=<generate-a-strong-random-key>
DB_HOST=crossover.proxy.rlwy.net
DB_PORT=32100
DB_USER=root
DB_PASSWORD=ycxutwYCeKTxYSLJMQsRSPUTKjKzYPkC
DB_NAME=railway
DEBUG=False
```

### 4. Deploy

Click "Create Web Service" and Render will automatically deploy your application.

Your API will be available at: `https://your-service-name.onrender.com`

## Testing the API

### Using cURL

```bash
# Register a user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Doe",
    "email": "john@example.com",
    "phone_number": "+639123456789",
    "password": "securepassword123",
    "user_type": "customer"
  }'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "securepassword123"
  }'

# Get current user (with token)
curl -X GET http://localhost:8000/users/me \
  -H "Authorization: Bearer <your-access-token>"
```

### Using Postman

1. Import the API collection
2. Set the base URL: `http://localhost:8000`
3. For protected endpoints, add Authorization header:
   - Type: Bearer Token
   - Token: `<your-access-token>`

## Database Schema

The application uses the existing MySQL database with tables:
- `users` - User accounts
- `riders` - Rider profiles
- `bill_requests` - Bill payment requests
- `payments` - Payment records
- `complaints` - Customer complaints
- `complaint_replies` - Admin replies
- `notifications` - User notifications
- `otps` - OTP codes
- `ratings` - Rider ratings
- `user_sessions` - Active sessions
- `user_preferences` - User settings
- `user_devices` - Registered devices
- `user_login_history` - Login logs
- `admin_users` - Admin profiles
- `blocked_tokens` - Revoked tokens

## Security

- Passwords are hashed using bcrypt
- JWT tokens for authentication
- Protected endpoints require valid tokens
- Role-based access control (customer, rider, admin)
- Environment variables for sensitive data

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License

## Support

For issues and questions, please open an issue on GitHub.