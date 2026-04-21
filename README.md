# Nexus Intelligent Chatbot System

An enterprise-grade intelligent assistant that enables both technical administrators and non-technical users to interact with infrastructure systems through natural language. Nexus integrates authentication, natural language processing, task execution, audit logging, self-correction, and calendar management into a cohesive platform.

## Table of Contents

- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Quick Start](#quick-start)
- [Configuration Guide](#configuration-guide)
- [API Endpoint Documentation](#api-endpoint-documentation)
- [Deployment Instructions](#deployment-instructions)
- [Testing Instructions](#testing-instructions)
- [Development](#development)
- [Contributing](#contributing)

## Features

- **Natural Language Processing**: Submit infrastructure commands in plain English
- **Intelligent Context Management**: System remembers recent conversation context for reference resolution
- **Write Action Confirmation**: Destructive operations require explicit confirmation
- **Sensitive Data Masking**: Passwords, API keys, and tokens are automatically masked in logs and responses
- **Comprehensive Audit Logging**: Immutable audit trail of all executions for compliance
- **Self-Correction Engine**: Analyzes errors and suggests fixes based on historical patterns
- **Calendar Integration**: Schedule meetings and set reminders using natural language
- **Role-Based Access Control**: Support for GENERAL and ADMIN user roles
- **Concurrent User Support**: Handles 50+ concurrent authenticated users
- **Extensible Script Registry**: Register custom infrastructure scripts for execution

## Architecture Overview

Nexus uses a **Layered Architecture** pattern with four primary layers:

```
┌─────────────────────────────────────────┐
│     Presentation Layer                  │
│  (React Client, REST API Endpoints)     │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│     Business Logic Layer                │
│  (NLP Engine, Context Manager,          │
│   Task Executor Orchestration)          │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│     Integration Layer                   │
│  (Script Registry, Calendar Integration,│
│   Authentication Service)               │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│     Data/Persistence Layer              │
│  (Audit Logger, Database, Context Cache)│
└─────────────────────────────────────────┘
```

### Key Components

- **NLP Engine**: Parses natural language commands using Gemini API and RAG service
- **Context Manager**: Maintains last 3 messages per user for reference resolution
- **Task Executor**: Orchestrates task execution with confirmation for write actions
- **Script Registry**: Manages registered infrastructure scripts
- **Audit Logger**: Maintains immutable execution logs
- **Self-Correction Engine**: Analyzes errors and suggests fixes
- **Calendar Integration**: Interfaces with external calendar APIs
- **Unified API Layer**: FastAPI-based REST API for all operations

## Quick Start

### Prerequisites

- Python 3.10+
- Docker and Docker Compose (for containerized deployment)
- Git

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd nexus
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   ```

3. **Update configuration**
   Edit `.env` with your API keys and configuration:
   ```bash
   GEMINI_API_KEY=your-gemini-api-key
   CALENDAR_API_KEY=your-calendar-api-key
   JWT_SECRET=your-secret-key
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Initialize database**
   ```bash
   python nexus/init_db.py
   ```

6. **Start the application**
   ```bash
   bash start.sh
   ```

   Or manually:
   ```bash
   uvicorn nexus.api:app --host 0.0.0.0 --port 8000 --reload
   ```

7. **Access the application**
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## Configuration Guide

### Environment Variables

All configuration is managed through environment variables. Copy `.env.example` to `.env` and update the values:

#### Authentication
- `JWT_SECRET`: Secret key for JWT token signing (change in production)
- `TOKEN_EXPIRY`: JWT token expiry time in seconds (default: 3600)
- `IDENTITY_PROVIDER_URL`: URL of the identity provider

#### Database
- `DATABASE_URL`: SQLite connection string (default: `sqlite:///./nexus_test.db`)
- `DATABASE_ECHO`: Enable SQL query logging (default: False)

#### External APIs
- `GEMINI_API_KEY`: Google Gemini API key for NLP processing
- `CALENDAR_API_KEY`: Calendar API key for scheduling
- `CALENDAR_API_URL`: Calendar API endpoint
- `DEFAULT_TIMEZONE`: Default timezone for calendar operations (default: UTC)

#### NLP Engine
- `CONFIDENCE_THRESHOLD`: Minimum confidence for intent classification (default: 0.5)
- `MIN_CONFIDENCE_FOR_EXECUTION`: Minimum confidence to execute tasks (default: 0.5)

#### Task Execution
- `MAX_CONCURRENT_TASKS`: Maximum concurrent tasks (default: 50)
- `TASK_TIMEOUT_SECONDS`: Task execution timeout (default: 300)
- `CONFIRMATION_PROMPT_EXPIRY_SECONDS`: Confirmation prompt expiry (default: 600)

#### Sensitive Data Masking
- `PASSWORD_PATTERN`: Regex pattern for password detection
- `API_KEY_PATTERN`: Regex pattern for API key detection
- `TOKEN_PATTERN`: Regex pattern for token detection

#### Server
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8000)
- `DEBUG`: Debug mode (default: False)

#### Logging
- `LOG_LEVEL`: Logging level (default: INFO)
- `LOG_FILE`: Log file path (default: nexus.log)

#### Context Manager
- `CONTEXT_MAX_SIZE`: Maximum messages in context (default: 3)
- `CONTEXT_TTL_SECONDS`: Context time-to-live (default: 3600)

#### Error Handling
- `RETRY_MAX_ATTEMPTS`: Maximum retry attempts (default: 3)
- `RETRY_BACKOFF_FACTOR`: Exponential backoff factor (default: 2)
- `EXTERNAL_API_TIMEOUT`: External API timeout (default: 30)

## API Endpoint Documentation

### Authentication Endpoints

#### Login
```
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password"
}

Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "email": "user@example.com",
    "role": "GENERAL"
  }
}
```

#### Register
```
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password"
}

Response:
{
  "email": "user@example.com",
  "role": "GENERAL"
}
```

### Command Execution Endpoints

#### Submit Command
```
POST /api/v1/command
Authorization: Bearer <token>
Content-Type: application/json

{
  "command": "Check the CPU usage on the main server"
}

Response:
{
  "intent": "query_metrics",
  "confidence": 0.95,
  "result": {
    "success": true,
    "output": "CPU Usage: 45%",
    "execution_time_ms": 250
  }
}
```

#### Confirm Action
```
POST /api/v1/confirm/{prompt_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "confirmed": true
}

Response:
{
  "success": true,
  "output": "Service restarted successfully",
  "execution_time_ms": 1200
}
```

### Script Management Endpoints (Admin Only)

#### Register Script
```
POST /api/v1/scripts
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Check CPU",
  "file_path": "/scripts/check_cpu.py",
  "language": "python",
  "mapped_intents": ["query_metrics"],
  "parameters": [
    {
      "name": "server",
      "type": "string",
      "required": true,
      "description": "Server name"
    }
  ],
  "is_read_only": true
}

Response:
{
  "success": true,
  "script_id": "check_cpu_v1"
}
```

#### List Scripts
```
GET /api/v1/scripts
Authorization: Bearer <token>

Response:
{
  "scripts": [
    {
      "script_id": "check_cpu_v1",
      "name": "Check CPU",
      "language": "python",
      "is_read_only": true,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### Audit Log Endpoints (Admin Only)

#### Retrieve Audit Logs
```
GET /api/v1/audit?user_id=user@example.com&start_date=2024-01-01&end_date=2024-01-31
Authorization: Bearer <token>

Response:
{
  "logs": [
    {
      "entry_id": "audit_123",
      "user_email": "user@example.com",
      "command": "Check CPU usage",
      "intent": "query_metrics",
      "success": true,
      "execution_time_ms": 250,
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### Calendar Endpoints

#### Schedule Meeting
```
POST /api/v1/calendar/schedule
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Team Standup",
  "start_time": "2024-01-20T10:00:00Z",
  "duration_minutes": 30,
  "attendees": ["team@example.com"]
}

Response:
{
  "success": true,
  "meeting_id": "meeting_123",
  "confirmation_message": "Meeting scheduled successfully"
}
```

#### Set Reminder
```
POST /api/v1/calendar/reminder
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Review deployment logs",
  "reminder_time": "2024-01-20T15:00:00Z",
  "description": "Check logs for any errors"
}

Response:
{
  "success": true
}
```

## Deployment Instructions

### Docker Compose Deployment

1. **Prepare environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Build and start services**
   ```bash
   docker-compose up -d
   ```

3. **Verify services are running**
   ```bash
   docker-compose ps
   ```

4. **View logs**
   ```bash
   docker-compose logs -f nexus-api
   ```

5. **Stop services**
   ```bash
   docker-compose down
   ```

### Manual Deployment

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Initialize database**
   ```bash
   python nexus/init_db.py
   ```

3. **Start services**
   ```bash
   # Terminal 1: Start Nexus API
   uvicorn nexus.api:app --host 0.0.0.0 --port 8000
   
   # Terminal 2: Start RAG Service
   cd model && python main.py
   
   # Terminal 3: Start Auth Service
   cd auth && uvicorn auth.main:app --host 0.0.0.0 --port 8002
   ```

### Production Deployment

For production deployment:

1. **Update `.env` with production values**
   - Change `JWT_SECRET` to a strong random value
   - Set `DEBUG=False`
   - Use PostgreSQL instead of SQLite for `DATABASE_URL`
   - Configure proper API keys for all external services

2. **Use a production ASGI server**
   ```bash
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker nexus.api:app
   ```

3. **Set up SSL/TLS**
   - Use a reverse proxy (nginx, Apache) with SSL certificates
   - Configure CORS appropriately

4. **Database backups**
   - Set up regular database backups
   - Test backup restoration procedures

5. **Monitoring and logging**
   - Configure centralized logging
   - Set up monitoring and alerting
   - Monitor API response times and error rates

## Testing Instructions

### Run All Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest nexus/test_nlp_engine.py

# Run specific test
pytest nexus/test_nlp_engine.py::test_parse_command
```

### Run Property-Based Tests

```bash
# Run all property tests
pytest -k "property" -v

# Run property tests with more iterations
pytest -k "property" --hypothesis-seed=0 -v
```

### Run Integration Tests

```bash
# Run integration tests
pytest -k "integration" -v

# Run specific integration test
pytest nexus/test_integration.py::test_complete_command_flow
```

### Test Coverage

```bash
# Generate coverage report
pytest --cov=nexus --cov=auth --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Unit Tests

Unit tests validate specific examples and edge cases:

```bash
pytest nexus/test_nlp_engine.py -v
pytest nexus/test_context_manager.py -v
pytest nexus/test_task_executor.py -v
pytest nexus/test_script_registry.py -v
pytest nexus/test_audit_logger.py -v
pytest nexus/test_self_correction_engine.py -v
pytest nexus/test_calendar_integration.py -v
```

### Property-Based Tests

Property-based tests validate universal properties across many generated inputs:

```bash
# Run property tests with Hypothesis
pytest nexus/test_*_properties.py -v

# Run with specific seed for reproducibility
pytest nexus/test_*_properties.py --hypothesis-seed=12345 -v
```

### Integration Tests

Integration tests validate end-to-end flows:

```bash
pytest nexus/test_integration.py -v
```

## Development

### Project Structure

```
nexus/
├── nexus/                          # Core application
│   ├── api.py                      # FastAPI application
│   ├── models.py                   # Data models
│   ├── database.py                 # Database operations
│   ├── config.py                   # Configuration management
│   ├── nlp_engine.py               # NLP processing
│   ├── context_manager.py          # Context management
│   ├── task_executor.py            # Task execution
│   ├── script_registry.py          # Script management
│   ├── audit_logger.py             # Audit logging
│   ├── self_correction_engine.py   # Error analysis
│   ├── calendar_integration.py     # Calendar operations
│   ├── error_handling.py           # Error utilities
│   ├── init_db.py                  # Database initialization
│   └── test_*.py                   # Test files
├── auth/                           # Authentication module
│   ├── auth.py                     # Auth logic
│   ├── models.py                   # Auth models
│   ├── database.py                 # Auth database
│   ├── main.py                     # Auth API
│   └── test_*.py                   # Auth tests
├── model/                          # RAG service
│   ├── main.py                     # RAG API
│   ├── rag_service.py              # RAG logic
│   └── docs/                       # Knowledge base
├── scripts/                        # Infrastructure scripts
│   ├── check_cpu.py
│   ├── check_memory.py
│   ├── check_disk.py
│   ├── check_service.sh
│   └── restart_service.sh
├── client/                         # React frontend
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   └── styles/
│   └── package.json
├── requirements.txt                # Python dependencies
├── docker-compose.yml              # Docker Compose configuration
├── Dockerfile                      # Main service Dockerfile
├── .env.example                    # Environment template
├── start.sh                        # Startup script
└── README.md                       # This file
```

### Adding New Features

1. **Define requirements** in `.kiro/specs/nexus-complete-system/requirements.md`
2. **Design the feature** in `.kiro/specs/nexus-complete-system/design.md`
3. **Create implementation tasks** in `.kiro/specs/nexus-complete-system/tasks.md`
4. **Implement with tests** following the task list
5. **Update documentation** as needed

### Code Style

- Follow PEP 8 for Python code
- Use type hints for all functions
- Write docstrings for all classes and functions
- Use meaningful variable and function names

### Git Workflow

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make changes and commit: `git commit -m "Add your feature"`
3. Push to remote: `git push origin feature/your-feature`
4. Create a pull request for review

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, questions, or suggestions:

1. Check existing issues on GitHub
2. Create a new issue with detailed description
3. Contact the development team

## Roadmap

- [ ] Multi-language support
- [ ] Advanced analytics dashboard
- [ ] Machine learning-based intent prediction
- [ ] Custom workflow builder
- [ ] Mobile app support
- [ ] Advanced security features (2FA, SSO)
- [ ] Performance optimization
- [ ] Kubernetes deployment support

---

**Last Updated**: January 2024
**Version**: 1.0.0
