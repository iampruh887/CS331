# Nexus Testing Documentation

This document outlines the testing strategy for the Nexus Intelligent Task Assistant system, covering both white box and black box testing approaches.

## White Box Testing

White box testing validates internal component logic, data structures, and implementation details.

### Component Testing

#### NLP Engine (nlp_engine.py)

Internal methods tested:
- _build_parse_prompt(): Validates prompt construction with user context
- _parse_gemini_response(): Tests JSON parsing and fallback handling
- _string_to_intent(): Validates intent enum conversion
- _infer_intent_from_text(): Tests keyword-based intent inference
- _extract_entities_with_patterns(): Validates regex pattern matching
- _calculate_confidence(): Tests confidence score calculation algorithm

Test cases:
- Confidence calculation with various entity counts
- Pattern matching for different entity types (server, service, time, metric)
- Intent inference from ambiguous text
- Fallback behavior when Gemini returns invalid JSON
- Edge cases: empty strings, special characters, malformed input

#### Task Executor (task_executor.py)

Internal methods tested:
- _build_script_parameters(): Validates entity-to-parameter mapping
- _build_confirmation_message(): Tests message formatting
- _mask_sensitive_data(): Validates regex pattern masking
- _invoke_script(): Tests subprocess execution and timeout handling
- _serialize_task() / _deserialize_task(): Tests JSON serialization
- requires_confirmation(): Validates write action detection

Test cases:
- Sensitive data masking for passwords, API keys, tokens, private keys
- Script parameter extraction from entities
- Confirmation prompt generation and expiry
- Script execution timeout handling
- Thread pool management and concurrent task limits
- Task serialization round-trip accuracy

#### Context Manager (context_manager.py)

Internal methods tested:
- update_context(): Validates message pruning (keeps last 3)
- resolve_reference(): Tests entity lookup by type
- _matches_reference(): Validates reference matching logic
- clear_context(): Tests context cleanup

Test cases:
- Message history pruning when exceeding max size
- Reference resolution for "it", "that", "the service"
- Entity type matching in context
- Context isolation between users
- Memory cleanup on user logout

#### Script Registry (script_registry.py)

Internal methods tested:
- _validate_script(): Validates script file existence and permissions
- _check_authorization(): Tests role-based access control
- find_scripts_by_intent(): Tests intent-to-script mapping

Test cases:
- Script validation for missing files
- Authorization checks for GENERAL vs ADMIN users
- Intent mapping with multiple scripts
- Duplicate script ID handling
- Parameter validation

#### Database (database.py)

Internal methods tested:
- get_connection(): Tests connection pooling and timeout
- initialize_schema(): Validates table creation
- Transaction handling: commit on success, rollback on error

Test cases:
- Schema initialization idempotency
- Connection timeout configuration
- Transaction rollback on constraint violations
- Concurrent connection handling
- Database error propagation

#### Configuration (config.py)

Internal methods tested:
- _load_configuration(): Tests environment variable loading
- _validate_configuration(): Validates parameter ranges and requirements
- get_database_path(): Tests URL parsing

Test cases:
- Missing required parameters (JWT_SECRET, GEMINI_API_KEY)
- Invalid parameter values (confidence threshold > 1.0)
- Short JWT_SECRET (< 32 characters)
- Default value application
- Environment variable precedence

### Algorithm Testing

#### Confidence Scoring Algorithm

Tests for confidence calculation in NLP Engine:
- Base confidence from Gemini response
- Boost for known intents (+0.1)
- Adjustment for entity count (+0.05 per entity)
- Penalty for error indicators (-0.2)
- Boundary conditions (0.0 to 1.0 range)

#### Pattern Matching Algorithm

Tests for entity extraction:
- Server name patterns (hostname, FQDN, IP)
- Service name patterns (systemd, docker, process names)
- Time expression patterns (relative, absolute, natural language)
- Metric patterns (cpu, memory, disk, network)
- Email patterns (RFC 5322 compliance)

#### Sensitive Data Masking Algorithm

Tests for regex pattern matching:
- Password patterns with various formats
- API key patterns (prefixed, quoted, unquoted)
- Token patterns (Bearer, JWT)
- Private key blocks (PEM format)
- AWS credentials (AKIA prefix)
- Generic key patterns (20+ character strings)

### Data Structure Testing

#### Message History

Tests for MessageHistory class:
- add_message() maintains max size of 3
- Messages stored in chronological order
- Oldest messages pruned first
- Empty history handling

#### Confirmation Prompt Storage

Tests for in-memory and database storage:
- Prompt expiry calculation
- Concurrent access with locks
- Memory-database synchronization
- Expired prompt cleanup

#### Task Queue Management

Tests for concurrent task execution:
- Thread pool size limits
- Task cancellation
- Active task tracking
- Queue overflow handling

## Black Box Testing

Black box testing validates external behavior, API contracts, and user-facing functionality without knowledge of internal implementation.

### API Endpoint Testing

#### POST /api/v1/command

Input validation:
- Command length (1-4000 characters)
- Empty command rejection
- Special character handling
- Unicode support

Response validation:
- Intent classification accuracy
- Confidence score range (0.0-1.0)
- Entity extraction completeness
- Execution result structure
- Error message clarity

Authentication:
- Valid JWT token required
- Expired token rejection
- Invalid token format handling
- Missing Authorization header

#### POST /api/v1/confirm/{prompt_id}

Input validation:
- Boolean confirmed field
- Valid prompt_id format
- Expired prompt handling

Response validation:
- Execution result on confirmation
- Cancellation message on rejection
- Execution time tracking
- Error handling for invalid prompt_id

Authorization:
- User can only confirm own prompts
- Admin cannot confirm other user prompts

#### POST /api/v1/scripts (Admin only)

Input validation:
- Script ID uniqueness
- File path existence
- Language enum validation (python, bash)
- Intent enum validation
- Parameter schema validation

Response validation:
- Success confirmation
- Script registration in database
- Error messages for duplicates

Authorization:
- GENERAL user rejection (403 Forbidden)
- ADMIN user acceptance

#### GET /api/v1/scripts

Response validation:
- Complete script list returned
- Correct JSON structure
- All fields present (script_id, name, file_path, language, etc.)
- Empty list for no scripts

#### GET /api/v1/audit

Query parameter validation:
- user_id filtering
- start_date / end_date ISO format
- intent filtering
- Invalid date format rejection

Response validation:
- Filtered results accuracy
- Chronological ordering
- Complete audit entry structure
- Empty list for no matches

Authorization:
- Admin-only access (403 for GENERAL users)

#### POST /api/v1/calendar/schedule

Input validation:
- ISO datetime format for start_time
- Positive duration_minutes
- Valid email format for attendees
- Title length limits

Response validation:
- Meeting ID generation
- Confirmation message
- Success boolean

#### POST /api/v1/calendar/reminder

Input validation:
- ISO datetime format for reminder_time
- Optional description field
- Title required

Response validation:
- Success boolean
- Confirmation message

### Model Query Testing

Tests for NLP model responses using actual queries.

#### Intent Classification Queries

Test queries with expected intents:

Query: "Check the status of nginx on web-server-01"
Expected: Intent.CHECK_STATUS, entities: [service:nginx, server:web-server-01]

Query: "Restart the mysql service"
Expected: Intent.RESTART_SERVICE, entities: [service:mysql]

Query: "Show me CPU and memory usage"
Expected: Intent.QUERY_METRICS, entities: [metric:cpu, metric:memory]

Query: "Schedule a meeting tomorrow at 3pm"
Expected: Intent.SCHEDULE_MEETING, entities: [time:tomorrow at 3pm]

Query: "Remind me to check logs in 2 hours"
Expected: Intent.SET_REMINDER, entities: [time:in 2 hours]

Query: "Register a new monitoring script"
Expected: Intent.REGISTER_SCRIPT

Query: "What is the meaning of life?"
Expected: Intent.UNKNOWN, confidence < 0.5

#### Entity Extraction Queries

Test queries with expected entities:

Query: "Restart nginx on prod-server-01.example.com"
Expected entities:
- EntityType.SERVICE: "nginx"
- EntityType.SERVER: "prod-server-01.example.com"

Query: "Check disk usage on all servers"
Expected entities:
- EntityType.METRIC: "disk"
- EntityType.SERVER: "all servers"

Query: "Schedule meeting with john@example.com tomorrow at 10:30am"
Expected entities:
- EntityType.USER_EMAIL: "john@example.com"
- EntityType.TIME: "tomorrow at 10:30am"

#### Confidence Score Validation

Test queries with expected confidence ranges:

High confidence (> 0.8):
- "Restart nginx service"
- "Check CPU usage"
- "Schedule meeting tomorrow"

Medium confidence (0.5-0.8):
- "Can you restart that thing?"
- "Show me the stats"
- "Set up a call"

Low confidence (< 0.5):
- "Do something with the server"
- "Fix it"
- "Help"

#### Context Resolution Queries

Test multi-turn conversations:

Turn 1: "Check status of nginx on web-server-01"
Turn 2: "Restart it"
Expected: Resolves "it" to nginx service

Turn 1: "Show metrics for prod-db-01"
Turn 2: "Check that server's disk space"
Expected: Resolves "that server" to prod-db-01

Turn 1: "Schedule meeting with team@example.com"
Turn 2: "Set reminder for that meeting"
Expected: Resolves "that meeting" to previous meeting

#### Sensitive Data Masking Validation

Test queries that should trigger masking:

Query: "Set password to MySecretPass123"
Expected output: "Set password to [PASSWORD_MASKED]"

Query: "Use API key sk-1234567890abcdef"
Expected output: "Use API key [API_KEY_MASKED]"

Query: "Token is eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
Expected output: "Token is [TOKEN_MASKED]"

### Integration Testing

End-to-end workflow tests:

#### Complete Command Flow

1. User submits command
2. NLP Engine parses intent and entities
3. Context Manager updates history
4. Script Registry finds matching script
5. Task Executor executes or prompts for confirmation
6. Audit Logger records execution
7. Response returned to user

Validation:
- All components invoked in correct order
- Data passed correctly between components
- Errors handled gracefully at each stage
- Audit log entry created

#### Write Action Confirmation Flow

1. User submits write action command
2. System generates confirmation prompt
3. Prompt stored in database with expiry
4. User confirms action
5. Task executed
6. Confirmation prompt removed
7. Audit log updated

Validation:
- Confirmation prompt generated correctly
- Expiry time calculated properly
- User authorization checked
- Prompt removed after confirmation
- Cancellation handled correctly

#### Context-Aware Command Flow

1. User submits command with entities
2. Context Manager stores message
3. User submits follow-up with reference
4. Context Manager resolves reference
5. Task executed with resolved entities

Validation:
- Context maintained across requests
- References resolved correctly
- Entity types matched properly
- Context pruned after 3 messages

### Performance Testing

Response time validation:
- Command parsing: < 2 seconds
- Script execution: < 30 seconds (configurable timeout)
- Database operations: < 100ms
- API endpoint response: < 3 seconds

Concurrency validation:
- 50 concurrent users (MAX_CONCURRENT_TASKS)
- No task queue overflow
- No database connection exhaustion
- No memory leaks

### Error Handling Testing

Error scenarios:
- Invalid JWT token
- Expired confirmation prompt
- Missing script file
- Script execution timeout
- Database connection failure
- Gemini API timeout
- Invalid intent value
- Malformed JSON in request

Expected behavior:
- Descriptive error messages
- Appropriate HTTP status codes
- No sensitive data in error responses
- Graceful degradation
- Audit log entry for failures

## Test Execution

Run all tests:
```bash
pytest nexus/
```

Run white box tests only:
```bash
pytest nexus/test_nlp_engine.py nexus/test_task_executor.py nexus/test_context_manager.py
```

Run black box tests only:
```bash
pytest nexus/test_integration.py nexus/test_calendar_integration.py
```

Run property-based tests:
```bash
pytest nexus/test_*_properties.py
```

Run with coverage:
```bash
pytest --cov=nexus --cov-report=html
```

## Test Data

Test fixtures:
- Sample scripts (Python and Bash)
- Mock users (GENERAL and ADMIN roles)
- Sample commands with various intents
- Mock Gemini API responses
- Sample audit log entries

Test databases:
- In-memory SQLite for unit tests
- Temporary file databases for integration tests
- Cleanup after each test

## Continuous Testing

Automated testing on:
- Every commit (unit tests)
- Pull requests (full test suite)
- Nightly builds (property-based tests with extended examples)
- Pre-deployment (integration tests against staging)


## Data Access Layer (DAL) Implementation

The Data Access Layer serves as an abstraction between the application logic and the SQLite database, providing a clean interface for all database operations.

### Architecture

The DAL is implemented in `nexus/database.py` as a single `Database` class that manages:
- Connection pooling and lifecycle
- Schema initialization
- CRUD operations for all tables
- Transaction management
- Error handling and rollback

### Database Schema

#### Tables

**users**
- id: INTEGER PRIMARY KEY AUTOINCREMENT
- email: TEXT UNIQUE NOT NULL
- hashed_password: TEXT NOT NULL
- is_active: BOOLEAN DEFAULT 1
- role: TEXT DEFAULT 'GENERAL'
- created_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- updated_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP

**scripts**
- script_id: TEXT PRIMARY KEY
- name: TEXT NOT NULL
- file_path: TEXT NOT NULL
- language: TEXT NOT NULL (python, bash)
- mapped_intents: TEXT NOT NULL (JSON array)
- parameters: TEXT NOT NULL (JSON array)
- is_read_only: BOOLEAN NOT NULL
- registered_by: TEXT NOT NULL (FOREIGN KEY to users.email)
- created_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP

**audit_logs** (immutable)
- entry_id: TEXT PRIMARY KEY
- user_id: TEXT NOT NULL
- user_email: TEXT NOT NULL (FOREIGN KEY to users.email)
- command: TEXT NOT NULL
- intent: TEXT NOT NULL
- success: BOOLEAN NOT NULL
- output: TEXT
- error: TEXT
- execution_time_ms: INTEGER NOT NULL
- timestamp: TIMESTAMP DEFAULT CURRENT_TIMESTAMP

Triggers:
- prevent_audit_update: Prevents UPDATE operations
- prevent_audit_delete: Prevents DELETE operations

**error_logs**
- error_id: TEXT PRIMARY KEY
- task_json: TEXT NOT NULL
- error_message: TEXT NOT NULL
- stack_trace: TEXT
- timestamp: TIMESTAMP DEFAULT CURRENT_TIMESTAMP

**error_patterns**
- pattern_id: TEXT PRIMARY KEY
- pattern_regex: TEXT NOT NULL
- description: TEXT NOT NULL
- common_causes: TEXT NOT NULL (JSON array)
- suggested_fixes: TEXT NOT NULL (JSON array)
- created_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP

**confirmation_prompts** (temporary storage)
- prompt_id: TEXT PRIMARY KEY
- message: TEXT NOT NULL
- task_json: TEXT NOT NULL
- user_id: TEXT NOT NULL
- expiry_time: TIMESTAMP NOT NULL
- confirmed: BOOLEAN
- created_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP

### Connection Management

The DAL uses a context manager pattern for connection handling:

```python
@contextmanager
def get_connection(self):
    conn = None
    try:
        conn = sqlite3.connect(self.db_path, timeout=config.DATABASE_OPERATION_TIMEOUT)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        yield conn
        conn.commit()
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        raise DatabaseError(f"Database operation failed: {str(e)}") from e
    finally:
        if conn:
            conn.close()
```

Features:
- Automatic commit on success
- Automatic rollback on error
- Connection cleanup in finally block
- Configurable timeout (DATABASE_OPERATION_TIMEOUT)
- Row factory for dictionary-like access

### DAL Operations

#### Script Registry Operations

**insert_script(script: Script) -> bool**
- Inserts new script into registry
- Returns False on duplicate script_id
- Serializes mapped_intents and parameters to JSON

**get_script(script_id: str) -> Optional[Script]**
- Retrieves script by ID
- Deserializes JSON fields to Python objects
- Returns None if not found

**find_scripts_by_intent(intent: Intent) -> List[Script]**
- Queries all scripts
- Filters by intent in mapped_intents array
- Returns list of matching scripts

**delete_script(script_id: str) -> bool**
- Deletes script by ID
- Returns True if deleted, False if not found

**list_all_scripts() -> List[Script]**
- Returns all registered scripts
- Deserializes all JSON fields

#### Audit Log Operations

**insert_audit_entry(entry: AuditEntry) -> bool**
- Inserts immutable audit log entry
- Cannot be updated or deleted (enforced by triggers)
- Serializes ExecutionResult to individual columns

**query_audit_logs(...) -> List[Dict[str, Any]]**
- Supports filtering by:
  - user_id
  - start_date / end_date
  - intent
  - success_only
- Returns results ordered by timestamp DESC
- Dynamic query building with parameterized queries

#### Error Pattern Operations

**insert_error_pattern(pattern: ErrorPattern) -> bool**
- Inserts error pattern for self-correction
- Serializes common_causes and suggested_fixes to JSON

**get_all_error_patterns() -> List[ErrorPattern]**
- Returns all error patterns
- Deserializes JSON arrays

#### Confirmation Prompt Operations

**insert_confirmation_prompt(...) -> bool**
- Stores temporary confirmation prompt
- Includes expiry_time for cleanup

**get_confirmation_prompt(prompt_id: str) -> Optional[Dict[str, Any]]**
- Retrieves prompt by ID
- Returns None if not found or expired

**update_confirmation_status(prompt_id: str, confirmed: bool) -> bool**
- Updates confirmation status after user response
- Returns True if updated

### Data Serialization

The DAL handles serialization between Python objects and database storage:

**JSON Serialization:**
- mapped_intents: List[Intent] -> JSON array of strings
- parameters: List[Parameter] -> JSON array of objects
- common_causes: List[str] -> JSON array
- suggested_fixes: List[str] -> JSON array
- task_json: Task object -> JSON string

**Deserialization:**
- _row_to_script(): Converts sqlite3.Row to Script object
- JSON fields parsed back to Python lists/dicts
- Enum values converted to Intent/ScriptLanguage enums
- ISO timestamp strings converted to datetime objects

### Transaction Management

All operations use the get_connection() context manager which provides:

**Automatic Commit:**
- Successful operations commit automatically
- No manual commit() calls needed in application code

**Automatic Rollback:**
- Any exception triggers rollback
- Database remains consistent on errors
- Original exception re-raised after rollback

**Connection Cleanup:**
- Connections always closed in finally block
- No connection leaks
- Timeout prevents hanging connections

### Error Handling

**DatabaseError Exception:**
- Custom exception for all database errors
- Wraps sqlite3.Error with descriptive messages
- Preserves original exception chain

**Constraint Violations:**
- UNIQUE constraint failures handled gracefully
- Foreign key violations raise DatabaseError
- Check constraint violations raise DatabaseError

**Immutability Enforcement:**
- Triggers prevent audit log modifications
- Raises ABORT error with descriptive message
- Ensures compliance and audit trail integrity

### Initialization

**initialize_schema():**
- Creates all tables if they don't exist
- Idempotent (safe to call multiple times)
- Creates triggers for audit log immutability
- Called during application startup

**Database File:**
- SQLite database file location from config
- Default: sqlite:///./nexus.db
- Configurable via DATABASE_URL environment variable

### Testing the DAL

#### White Box DAL Tests

**Connection Management:**
- Test connection timeout configuration
- Test automatic commit on success
- Test automatic rollback on error
- Test connection cleanup in finally block
- Test concurrent connections

**Schema Initialization:**
- Test table creation
- Test idempotency (multiple calls)
- Test trigger creation
- Test foreign key constraints
- Test default values

**CRUD Operations:**
- Test insert with valid data
- Test insert with duplicate keys
- Test select by primary key
- Test select with filters
- Test update operations
- Test delete operations
- Test list all operations

**Serialization:**
- Test JSON serialization of complex types
- Test deserialization to Python objects
- Test enum conversion
- Test datetime conversion
- Test null value handling

**Transaction Handling:**
- Test commit on successful operation
- Test rollback on exception
- Test nested transaction behavior
- Test concurrent transaction isolation

**Immutability Enforcement:**
- Test audit log update prevention
- Test audit log delete prevention
- Test trigger error messages

#### Black Box DAL Tests

**Data Persistence:**
- Insert data and verify retrieval
- Update data and verify changes
- Delete data and verify removal
- Query with filters and verify results

**Data Integrity:**
- Test foreign key constraints
- Test unique constraints
- Test not null constraints
- Test check constraints

**Query Correctness:**
- Test filtering by user_id
- Test date range filtering
- Test intent filtering
- Test combined filters
- Test result ordering

**Error Scenarios:**
- Test invalid script_id
- Test expired confirmation prompts
- Test missing foreign key references
- Test invalid JSON in serialized fields

**Performance:**
- Test query response time
- Test bulk insert performance
- Test concurrent access
- Test large result set handling

### DAL Usage in Components

**Script Registry (script_registry.py):**
```python
def register_script(self, script: Script, user: User) -> bool:
    return db.insert_script(script)

def get_script(self, script_id: str) -> Optional[Script]:
    return db.get_script(script_id)
```

**Audit Logger (audit_logger.py):**
```python
async def log_execution(self, entry: AuditEntry) -> bool:
    return db.insert_audit_entry(entry)

async def retrieve_logs(self, filter: LogFilter) -> List[AuditEntry]:
    return db.query_audit_logs(
        user_id=filter.user_id,
        start_date=filter.start_date,
        end_date=filter.end_date,
        intent=filter.intent
    )
```

**Task Executor (task_executor.py):**
```python
def execute_with_confirmation(self, task: Task, user: User) -> ConfirmationPrompt:
    db.insert_confirmation_prompt(
        prompt_id=prompt_id,
        message=message,
        task_json=task_json,
        user_id=user.user_id,
        expiry_time=expiry_time
    )

def confirm_and_execute(self, prompt_id: str, confirmed: bool, user: User):
    prompt_data = db.get_confirmation_prompt(prompt_id)
    db.update_confirmation_status(prompt_id, confirmed)
```

**Self-Correction Engine (self_correction_engine.py):**
```python
def __init__(self):
    self.error_patterns = db.get_all_error_patterns()

def _identify_pattern(self, error: ExecutionError) -> Optional[ErrorPattern]:
    for pattern in self.error_patterns:
        if re.search(pattern.pattern_regex, error.error_message):
            return pattern
```

### DAL Benefits

**Abstraction:**
- Application code doesn't know about SQL
- Easy to switch database backends
- Centralized database logic

**Consistency:**
- Single source of truth for schema
- Consistent error handling
- Uniform transaction management

**Maintainability:**
- Database changes isolated to DAL
- Easy to add new operations
- Clear separation of concerns

**Testability:**
- Mock Database class for unit tests
- Test database operations independently
- Verify data integrity constraints

**Security:**
- Parameterized queries prevent SQL injection
- No raw SQL in application code
- Centralized access control
