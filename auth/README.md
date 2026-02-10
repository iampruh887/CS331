# Nexus Auth API

Simple email-based authentication system using FastAPI and JWT tokens.

## Features

- User registration with email validation
- Login with JWT token generation
- Password hashing with bcrypt
- Protected routes with token verification
- In-memory database (easy to swap for PostgreSQL/MongoDB later)

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Copy .env.example to .env (already done)
cp .env.example .env

# Run the server
python main.py
```

Server runs on `http://localhost:8000`

## API Endpoints

### POST /register
Register a new user
```json
{
  "email": "user@example.com",
  "password": "yourpassword"
}
```

### POST /login
Login and get access token
```json
{
  "email": "user@example.com",
  "password": "yourpassword"
}
```

Returns:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

### GET /me
Get current user info (requires auth header)
```
Authorization: Bearer <token>
```

## Testing

```bash
# Run test script
python test_api.py
```

Or use the interactive docs at `http://localhost:8000/docs`

## Project Structure

```
nexus_auth/
├── main.py          # FastAPI app and routes
├── auth.py          # Authentication utilities
├── models.py        # Pydantic models
├── database.py      # In-memory user storage
├── config.py        # Settings management
├── requirements.txt # Dependencies
├── .env            # Environment variables
└── test_api.py     # API tests
```

## Security Notes

- Passwords are hashed using bcrypt
- JWT tokens expire after 30 minutes (configurable)
- Change SECRET_KEY in .env for production
- Current setup uses in-memory storage (data lost on restart)

## Next Steps

- Add PostgreSQL/MongoDB for persistent storage
- Add email verification
- Add password reset functionality
- Add refresh tokens
- Add rate limiting
