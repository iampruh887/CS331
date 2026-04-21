# Nexus Core Module

The core business logic module for the Nexus Intelligent Task Assistant system.

## What This Module Does

This module handles natural language processing, task execution, context management, and calendar integration. It receives commands from users, parses them using AI, executes appropriate scripts, and returns results.

## Key Components

### NLP Engine (nlp_engine.py)
Parses natural language commands into structured intents and entities using Google's Gemini API. Returns confidence scores and falls back to clarification prompts when confidence is low.

### Context Manager (context_manager.py)
Maintains the last 3 messages per user to enable reference resolution. Allows users to say "restart it" or "check that server" by looking up recent entities from conversation history.

### Task Executor (task_executor.py)
Orchestrates script execution with confirmation prompts for write actions. Masks sensitive data (passwords, API keys, tokens) in all outputs using regex patterns.

### Script Registry (script_registry.py)
Manages registered infrastructure scripts. Supports Python and Bash scripts with parameter validation. Enforces read-only vs write permissions.

### Calendar Integration (calendar_integration.py)
Interfaces with external calendar APIs for availability checking, meeting scheduling, and reminder creation. Parses natural language time expressions.

### Audit Logger (audit_logger.py)
Records all command executions with timestamps, user info, success/failure status, and execution time. Provides immutable audit trail for compliance.

### Self-Correction Engine (self_correction_engine.py)
Analyzes execution errors against known patterns and suggests fixes based on common causes and solutions stored in the database.

### Database (database.py)
SQLite-based persistence layer. Manages users, scripts, audit logs, error logs, error patterns, and confirmation prompts.

### API (api.py)
FastAPI REST endpoints for command submission, confirmation handling, script management, and audit log retrieval. Requires JWT authentication.

## Configuration

All configuration is loaded from environment variables via config.py:

Required:
- JWT_SECRET: Secret key for JWT tokens (minimum 32 characters)
- GEMINI_API_KEY: Google Gemini API key for NLP processing
- DATABASE_URL: SQLite database path (default: sqlite:///./nexus.db)

Optional:
- CONFIDENCE_THRESHOLD: Minimum confidence for intent classification (default: 0.5)
- MAX_CONCURRENT_TASKS: Maximum concurrent task executions (default: 50)
- TOKEN_EXPIRY_MINUTES: JWT token expiration time (default: 30)
- CALENDAR_API_KEY: External calendar API key (optional)

## Database Schema

Tables:
- users: User accounts with email, hashed password, role (GENERAL/ADMIN)
- scripts: Registered infrastructure scripts with intent mappings
- audit_logs: Immutable execution history
- error_logs: Error occurrences with stack traces
- error_patterns: Known error patterns with suggested fixes
- confirmation_prompts: Pending write action confirmations

## Running the Module

From project root:

```bash
uvicorn nexus.api:app --host 0.0.0.0 --port 8002 --reload
```

Initialize database first:

```bash
python -m nexus.init_db
```

## Testing

Run all tests:

```bash
pytest nexus/
```

Run specific test file:

```bash
pytest nexus/test_nlp_engine.py -v
```

Run property-based tests:

```bash
pytest nexus/test_*_properties.py -v
```

## Dependencies

See requirements.txt for full list. Key dependencies:
- fastapi: REST API framework
- google-generativeai: Gemini API client
- python-jose: JWT token handling
- sqlalchemy: Database ORM
- dateparser: Natural language time parsing
- pytest + hypothesis: Testing frameworks

## Architecture

This module follows a layered architecture:

1. API Layer (api.py): HTTP endpoints and request/response handling
2. Business Logic Layer: NLP Engine, Task Executor, Context Manager
3. Integration Layer: Script Registry, Calendar Integration
4. Data Layer: Database, Audit Logger

All components are loosely coupled and can be tested independently.

## Security Features

- JWT-based authentication required for all operations
- Role-based access control (GENERAL vs ADMIN users)
- Write action confirmation prompts for destructive operations
- Sensitive data masking in outputs and logs
- Immutable audit trail for compliance
- Script execution timeout limits
- Parameter validation for all script inputs

## Error Handling

The system uses a self-correction approach:
1. Execution errors are logged with full context
2. Error patterns are matched against known issues
3. Suggested fixes are returned to the user
4. Historical error data improves future suggestions

## Context Management

Users can reference previous entities:
- "Check the status of server-01" followed by "restart it"
- "Show metrics for nginx" followed by "check that service"

The context manager maintains the last 3 messages per user and resolves references by entity type.

## Intent Classification

Supported intents:
- CHECK_STATUS: Check service or system status
- RESTART_SERVICE: Restart a service
- QUERY_METRICS: Query system metrics
- SCHEDULE_MEETING: Schedule a calendar meeting
- SET_REMINDER: Create a reminder
- REGISTER_SCRIPT: Register a new script (admin only)
- UNKNOWN: Unrecognized intent (triggers clarification)

## Confirmation Flow

Write actions require explicit confirmation:
1. User submits command: "restart nginx"
2. System detects write action and creates confirmation prompt
3. User receives prompt with details and prompt_id
4. User confirms or cancels via /api/v1/confirm/{prompt_id}
5. System executes or cancels based on user response

Confirmation prompts expire after 5 minutes.
