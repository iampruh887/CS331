# Implementation Plan: Nexus Intelligent Chatbot System

## Overview

This implementation plan breaks down the Nexus system into discrete, incremental tasks that build upon existing implementations (auth, chat, RAG service) and add the missing components. Each task is designed to be completed by a code-generation agent, with tasks building on previous work to create a fully integrated system.

The implementation follows this order:
1. Database schema and core data models
2. NLP Engine integration
3. Context Manager
4. Script Registry
5. Task Executor with confirmation
6. Audit Logger
7. Self-Correction Engine
8. Calendar Integration
9. Unified API layer
10. Integration and testing

## Tasks

- [x] 1. Set up project structure and database schema
  - Create `nexus/` directory for core components
  - Create database initialization script with all tables (users, scripts, audit_logs, error_logs, error_patterns, confirmation_prompts)
  - Create `nexus/models.py` with all data classes (ParsedIntent, Entity, Task, ExecutionResult, Script, AuditEntry, etc.)
  - Create `nexus/database.py` with database connection and helper functions
  - Set up configuration management in `nexus/config.py` for all environment variables
  - _Requirements: 15.1, 15.2, 15.3, 15.5_

- [x] 1.1 Write unit tests for database initialization
  - Test table creation
  - Test database connection handling
  - Test configuration loading with valid and invalid values
  - _Requirements: 15.1, 15.3_

- [x] 2. Implement NLP Engine with Gemini integration
  - [x] 2.1 Create `nexus/nlp_engine.py` with NLPEngine class
    - Integrate with existing Gemini API from `chat/chat_api.py`
    - Integrate with existing RAG service from `model/rag_service.py`
    - Implement `parse_command()` method to extract intent and entities
    - Implement intent classification using Gemini with structured prompts
    - Implement entity extraction for server names, service names, times, metrics
    - Implement confidence score calculation
    - _Requirements: 2.1, 2.3, 2.4, 2.5_

  - [x]* 2.2 Write property test for command parsing
    - **Property 5: Command parsing produces structured output**
    - **Validates: Requirements 2.1, 2.5**

  - [x]* 2.3 Write property test for low confidence fallback
    - **Property 6: Low confidence triggers fallback**
    - **Validates: Requirements 2.3**

  - [x]* 2.4 Write property test for entity extraction
    - **Property 7: Entity extraction by type**
    - **Validates: Requirements 2.4**

  - [x]* 2.5 Write unit tests for NLP Engine
    - Test specific intent examples (restart service, check status, query metrics)
    - Test edge cases (empty input, very long input, special characters)
    - Test Gemini API error handling
    - _Requirements: 2.1, 2.3_

- [ ] 3. Implement Context Manager
  - [x] 3.1 Create `nexus/context_manager.py` with ContextManager class
    - Implement in-memory context storage with user_id keys
    - Implement `get_context()` to retrieve user's message history
    - Implement `update_context()` to add messages and prune to 3 messages
    - Implement `resolve_reference()` to resolve "it", "that server", etc.
    - Implement `clear_context()` for session cleanup
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x]* 3.2 Write property test for context size invariant
    - **Property 8: Context size invariant**
    - **Validates: Requirements 3.1, 3.3**

  - [x]* 3.3 Write property test for reference resolution
    - **Property 9: Reference resolution**
    - **Validates: Requirements 3.2**

  - [x]* 3.4 Write property test for user context isolation
    - **Property 10: User context isolation**
    - **Validates: Requirements 3.5, 11.5**

  - [x]* 3.5 Write unit tests for Context Manager
    - Test empty context initialization
    - Test context pruning with various message counts
    - Test reference resolution with missing context
    - _Requirements: 3.1, 3.2, 3.4_

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement Script Registry
  - [x] 5.1 Create `nexus/script_registry.py` with ScriptRegistry class
    - Implement `register_script()` with admin authorization check
    - Implement `get_script()` to retrieve by script_id
    - Implement `find_scripts_by_intent()` for intent mapping
    - Implement `unregister_script()` with admin authorization
    - Implement `list_all_scripts()` for admin viewing
    - Add database operations for scripts table
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ]* 5.2 Write property test for script registration
    - **Property 11: Script registration with metadata**
    - **Validates: Requirements 4.1, 4.2**

  - [ ]* 5.3 Write property test for read-only flag preservation
    - **Property 12: Read-only flag preservation**
    - **Validates: Requirements 4.3**

  - [ ]* 5.4 Write property test for script ID uniqueness
    - **Property 13: Script ID uniqueness**
    - **Validates: Requirements 4.4**

  - [ ]* 5.5 Write property test for intent mapping
    - **Property 14: Intent mapping storage**
    - **Validates: Requirements 4.5**

  - [ ]* 5.6 Write unit tests for Script Registry
    - Test registration with invalid metadata
    - Test retrieval of non-existent scripts
    - Test authorization checks (GENERAL user attempting registration)
    - _Requirements: 4.1, 4.4_

- [x] 6. Implement Task Executor with confirmation
  - [x] 6.1 Create `nexus/task_executor.py` with TaskExecutor class
    - Implement `execute_task()` main orchestration method
    - Implement `requires_confirmation()` to check if write action
    - Implement `execute_with_confirmation()` to generate ConfirmationPrompt
    - Implement `confirm_and_execute()` to handle confirmation responses
    - Implement `_invoke_script()` to execute Python/Bash scripts using subprocess
    - Implement `_mask_sensitive_data()` with regex patterns for passwords, keys, tokens
    - Add task queue management with max 50 concurrent tasks
    - Store confirmation prompts in database with expiry
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3, 6.4, 6.5, 11.2, 11.3_

  - [ ]* 6.2 Write property test for write action confirmation
    - **Property 15: Write actions require confirmation**
    - **Validates: Requirements 5.1**

  - [ ]* 6.3 Write property test for confirmed action execution
    - **Property 16: Confirmed actions execute**
    - **Validates: Requirements 5.2**

  - [ ]* 6.4 Write property test for canceled action abort
    - **Property 17: Canceled actions abort**
    - **Validates: Requirements 5.3**

  - [ ]* 6.5 Write property test for read action immediate execution
    - **Property 18: Read actions execute immediately**
    - **Validates: Requirements 5.4, 10.4**

  - [ ]* 6.6 Write property test for sensitive data masking
    - **Property 19: Sensitive data is masked**
    - **Validates: Requirements 6.1, 6.2**

  - [ ]* 6.7 Write property test for masking in multiple outputs
    - **Property 20: Masking in multiple outputs**
    - **Validates: Requirements 6.3**

  - [ ]* 6.8 Write property test for clean output unchanged
    - **Property 21: Clean output unchanged**
    - **Validates: Requirements 6.5**

  - [ ]* 6.9 Write property test for task queue capacity
    - **Property 40: Task queue capacity**
    - **Validates: Requirements 11.2, 11.3**

  - [ ]* 6.10 Write unit tests for Task Executor
    - Test script execution with valid and invalid scripts
    - Test timeout handling for long-running scripts
    - Test confirmation prompt expiry
    - Test error handling for script failures
    - _Requirements: 5.1, 5.5, 6.1_

- [x] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement Audit Logger
  - [x] 8.1 Create `nexus/audit_logger.py` with AuditLogger class
    - Implement `log_execution()` to create and persist AuditEntry
    - Implement `retrieve_logs()` with filtering by user, date, intent
    - Implement `_format_entry()` for database storage
    - Add database operations for audit_logs table (append-only)
    - Ensure immutability with database constraints
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ]* 8.2 Write property test for audit entry creation
    - **Property 22: Audit entry creation**
    - **Validates: Requirements 7.1, 7.5**

  - [ ]* 8.3 Write property test for immediate persistence
    - **Property 23: Immediate persistence**
    - **Validates: Requirements 7.2**

  - [ ]* 8.4 Write property test for audit log immutability
    - **Property 24: Audit log immutability**
    - **Validates: Requirements 7.3**

  - [ ]* 8.5 Write property test for log filtering
    - **Property 25: Log filtering**
    - **Validates: Requirements 7.4**

  - [ ]* 8.6 Write unit tests for Audit Logger
    - Test logging with various execution results
    - Test filtering with edge cases (empty results, invalid dates)
    - Test database error handling
    - _Requirements: 7.1, 7.2, 7.4_

- [x] 9. Implement Self-Correction Engine
  - [x] 9.1 Create `nexus/self_correction_engine.py` with SelfCorrectionEngine class
    - Implement `analyze_error()` to identify patterns and suggest fixes
    - Implement `store_error()` to persist errors to database
    - Implement `_identify_pattern()` using regex matching against error_patterns table
    - Implement `_generate_suggestions()` based on matched patterns
    - Seed error_patterns table with common patterns (connection refused, permission denied, file not found, etc.)
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [ ]* 9.2 Write property test for error analysis
    - **Property 31: Error analysis on failure**
    - **Validates: Requirements 9.1**

  - [ ]* 9.3 Write property test for pattern identification
    - **Property 32: Pattern identification**
    - **Validates: Requirements 9.2**

  - [ ]* 9.4 Write property test for suggestions generation
    - **Property 33: Suggestions for known patterns**
    - **Validates: Requirements 9.3**

  - [ ]* 9.5 Write property test for error storage
    - **Property 34: Error storage**
    - **Validates: Requirements 9.4**

  - [ ]* 9.6 Write property test for unknown error fallback
    - **Property 35: Fallback for unknown errors**
    - **Validates: Requirements 9.5**

  - [ ]* 9.7 Write unit tests for Self-Correction Engine
    - Test with specific error patterns
    - Test with multiple matching patterns
    - Test pattern seeding
    - _Requirements: 9.1, 9.2, 9.5_

- [x] 10. Implement Calendar Integration
  - [x] 10.1 Create `nexus/calendar_integration.py` with CalendarIntegration class
    - Implement `check_availability()` with Calendar API calls
    - Implement `book_meeting()` with Calendar API calls
    - Implement `set_reminder()` with Calendar API calls
    - Implement `_parse_natural_language_time()` using dateparser library
    - Add error handling for API failures
    - Add timeout configuration for API calls
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [x]* 10.2 Write property test for availability checking
    - **Property 26: Availability checking**
    - **Validates: Requirements 8.1**

  - [x]* 10.3 Write property test for meeting booking
    - **Property 27: Meeting booking on availability**
    - **Validates: Requirements 8.2**

  - [x]* 10.4 Write property test for reminder creation
    - **Property 28: Reminder creation**
    - **Validates: Requirements 8.3**

  - [x]* 10.5 Write property test for time parsing
    - **Property 29: Natural language time parsing**
    - **Validates: Requirements 8.4**

  - [x]* 10.6 Write property test for calendar error handling
    - **Property 30: Calendar error handling**
    - **Validates: Requirements 8.5**

  - [x]* 10.7 Write unit tests for Calendar Integration
    - Test with mocked Calendar API
    - Test various time expression formats
    - Test API timeout handling
    - _Requirements: 8.1, 8.4, 8.5_

- [x] 11. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Implement Unified API Layer
  - [x] 12.1 Create `nexus/api.py` with FastAPI application
    - Integrate existing auth module for authentication
    - Implement POST `/api/v1/command` endpoint for command execution
    - Implement POST `/api/v1/confirm/{prompt_id}` endpoint for confirmations
    - Implement POST `/api/v1/scripts` endpoint for script registration (admin only)
    - Implement GET `/api/v1/scripts` endpoint to list scripts
    - Implement GET `/api/v1/audit` endpoint for audit logs (admin only)
    - Implement POST `/api/v1/calendar/schedule` endpoint for meeting scheduling
    - Implement POST `/api/v1/calendar/reminder` endpoint for reminders
    - Add CORS middleware configuration
    - Add error handling middleware
    - Add request logging middleware
    - _Requirements: 13.1, 13.2, 13.3, 13.5_

  - [ ]* 12.2 Write property test for token propagation
    - **Property 43: Token propagation**
    - **Validates: Requirements 13.2**

  - [ ]* 12.3 Write property test for graceful component failure
    - **Property 44: Graceful component failure**
    - **Validates: Requirements 13.3**

  - [ ]* 12.4 Write unit tests for API endpoints
    - Test each endpoint with valid and invalid inputs
    - Test authentication and authorization
    - Test error response formats
    - _Requirements: 13.1, 13.2_

- [x] 13. Implement authentication and authorization extensions
  - [x] 13.1 Extend `auth/auth.py` with role-based authorization
    - Add `require_admin()` dependency for admin-only endpoints
    - Add `get_current_user_with_role()` to return user with role
    - _Requirements: 1.4, 1.5_

  - [x]* 13.2 Write property test for valid credentials
    - **Property 1: Valid credentials produce JWT tokens**
    - **Validates: Requirements 1.1**

  - [x]* 13.3 Write property test for invalid credentials
    - **Property 2: Invalid credentials are rejected**
    - **Validates: Requirements 1.2**

  - [x]* 13.4 Write property test for token validation
    - **Property 3: Token validation occurs before processing**
    - **Validates: Requirements 1.3**

  - [x]* 13.5 Write property test for role-based access control
    - **Property 4: Role-based access control**
    - **Validates: Requirements 1.5**

- [x] 14. Implement error handling and resilience
  - [x] 14.1 Create `nexus/error_handling.py` with error handling utilities
    - Implement retry decorator with exponential backoff
    - Implement timeout decorator for external API calls
    - Implement exception logging utility
    - Implement input validation decorators
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

  - [ ]* 14.2 Write property test for external service unavailability
    - **Property 45: External service unavailability**
    - **Validates: Requirements 14.1**

  - [ ]* 14.3 Write property test for retry with exponential backoff
    - **Property 46: Retry with exponential backoff**
    - **Validates: Requirements 14.2**

  - [ ]* 14.4 Write property test for database error handling
    - **Property 47: Database error handling**
    - **Validates: Requirements 14.3**

  - [ ]* 14.5 Write property test for input validation
    - **Property 48: Input validation**
    - **Validates: Requirements 14.4**

  - [ ]* 14.6 Write property test for unhandled exception logging
    - **Property 49: Unhandled exception logging**
    - **Validates: Requirements 14.5**

  - [ ]* 14.7 Write unit tests for error handling utilities
    - Test retry logic with various failure scenarios
    - Test timeout behavior
    - Test exception logging format
    - _Requirements: 14.2, 14.5_

- [x] 15. Implement configuration management
  - [x] 15.1 Update `nexus/config.py` with all configuration parameters
    - Add JWT_SECRET, TOKEN_EXPIRY, DATABASE_URL
    - Add GEMINI_API_KEY, CALENDAR_API_KEY
    - Add CONFIDENCE_THRESHOLD, MAX_CONCURRENT_TASKS
    - Add timeout configurations
    - Add validation for required parameters
    - Add default values for optional parameters
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5_

  - [ ]* 15.2 Write property test for configuration loading
    - **Property 50: Configuration loading**
    - **Validates: Requirements 15.1**

  - [ ]* 15.3 Write property test for configuration parameter support
    - **Property 51: Configuration parameter support**
    - **Validates: Requirements 15.2**

  - [ ]* 15.4 Write property test for invalid configuration rejection
    - **Property 52: Invalid configuration rejection**
    - **Validates: Requirements 15.3**

  - [ ]* 15.5 Write property test for configuration defaults
    - **Property 53: Configuration defaults**
    - **Validates: Requirements 15.5**

- [x] 16. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [-] 17. Create sample scripts for testing
  - [x] 17.1 Create sample infrastructure scripts
    - Create `scripts/check_cpu.py` for CPU metrics
    - Create `scripts/check_memory.py` for memory metrics
    - Create `scripts/check_disk.py` for disk space
    - Create `scripts/check_service.sh` for service status
    - Create `scripts/restart_service.sh` for service restart (write action)
    - Add proper error handling and output formatting in scripts
    - _Requirements: 10.1, 10.2_

  - [ ]* 17.2 Write property test for metric query execution
    - **Property 36: Metric query execution**
    - **Validates: Requirements 10.1**

  - [ ]* 17.3 Write property test for metric type support
    - **Property 37: Metric type support**
    - **Validates: Requirements 10.2**

  - [ ]* 17.4 Write property test for metric response formatting
    - **Property 38: Metric response formatting**
    - **Validates: Requirements 10.3**

  - [ ]* 17.5 Write property test for metric error handling
    - **Property 39: Metric error handling**
    - **Validates: Requirements 10.5**

- [x] 18. Create database initialization and seeding
  - [x] 18.1 Create `nexus/init_db.py` script
    - Initialize all database tables
    - Seed error_patterns table with common patterns
    - Create default admin user
    - Register sample scripts in Script Registry
    - _Requirements: 4.1, 9.2_

  - [ ]* 18.2 Write unit tests for database initialization
    - Test table creation
    - Test seeding with various data
    - Test idempotency (running init multiple times)
    - _Requirements: 4.1_

- [x] 19. Integration testing and end-to-end flows
  - [x]* 19.1 Write integration test for complete command flow
    - Test: User login → Submit command → NLP parsing → Context enrichment → Task execution → Audit logging
    - **Validates: Requirements 13.1**

  - [x]* 19.2 Write integration test for write action with confirmation
    - Test: Submit write action → Confirmation prompt → Confirm → Execute → Audit log
    - _Requirements: 5.1, 5.2, 7.1_

  - [x]* 19.3 Write integration test for calendar scheduling
    - Test: Submit meeting request → Parse time → Check availability → Book meeting
    - _Requirements: 8.1, 8.2, 8.4_

  - [x]* 19.4 Write integration test for error correction
    - Test: Execute failing task → Store error → Analyze pattern → Return suggestions
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

  - [x]* 19.5 Write integration test for context resolution
    - Test: Submit command with entity → Submit follow-up with reference → Resolve reference → Execute
    - _Requirements: 3.1, 3.2_

- [x] 20. Update React client to use new API
  - [x] 20.1 Update `client/src/App.jsx` to call unified API
    - Update command submission to POST `/api/v1/command`
    - Add confirmation dialog for write actions
    - Add error display for various error codes
    - Add loading states for async operations
    - _Requirements: 13.5_

  - [x] 20.2 Write unit tests for React components
    - Test command submission
    - Test confirmation dialog
    - Test error display
    - _Requirements: 13.5_

- [x] 21. Create deployment and documentation
  - [x] 21.1 Create deployment scripts
    - Create `docker-compose.yml` for containerized deployment
    - Create `requirements.txt` with all Python dependencies
    - Create `.env.example` with all configuration parameters
    - Create startup script `start.sh` to initialize database and start services
    - _Requirements: 15.1, 15.2_

  - [x] 21.2 Update README.md with complete documentation
    - Add architecture overview
    - Add API endpoint documentation
    - Add configuration guide
    - Add deployment instructions
    - Add testing instructions
    - _Requirements: 13.5_

- [-] 22. Final checkpoint - Complete system validation
  - Run all unit tests
  - Run all property tests
  - Run all integration tests
  - Verify all 53 correctness properties pass
  - Test with sample scripts
  - Verify audit logging works
  - Verify error correction works
  - Verify calendar integration works (with mock API)
  - Ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties (minimum 100 iterations each)
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end flows
- The implementation builds on existing auth, chat, and RAG modules
- All components use Python 3.10+ with FastAPI
- Database uses SQLite for development (can migrate to PostgreSQL for production)
- Testing uses pytest and Hypothesis for property-based testing
