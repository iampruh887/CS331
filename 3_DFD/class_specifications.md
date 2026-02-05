# Class Specifications for Nexus Intelligent Chatbot System

## 1. User (Abstract Base Class)

### Attributes:
- **- userId: String** (private) - Unique identifier for the user
- **- username: String** (private) - User's login name
- **- authToken: String** (private) - Authentication token
- **- role: UserRole** (private) - User role (GENERAL, ADMIN)
- **- isAuthenticated: Boolean** (private) - Authentication status

### Methods:
- **+ authenticate(credentials: Credentials): Boolean** (public) - Authenticate user
- **+ submitCommand(command: String): CommandResult** (public) - Submit natural language command
- **+ viewResults(result: ExecutionResult): void** (public) - View execution results
- **+ getUserId(): String** (public) - Get user ID
- **+ getRole(): UserRole** (public) - Get user role
- **# setAuthToken(token: String): void** (protected) - Set authentication token
- **# validatePermissions(): Boolean** (protected) - Validate user permissions

---

## 2. Administrator (Inherits from User)

### Attributes:
- **- registeredScripts: List<Script>** (private) - List of scripts registered by this admin

### Methods:
- **+ registerScript(script: Script): Boolean** (public) - Register new external script
- **+ executeWriteAction(command: Command): ExecutionResult** (public) - Execute state-changing tasks
- **+ confirmAction(confirmationId: String): Boolean** (public) - Confirm write actions
- **+ viewErrorAnalysis(errorId: String): ErrorAnalysis** (public) - View self-correction suggestions
- **+ querySystemMetrics(query: MetricQuery): MetricData** (public) - Query system metrics

---

## 3. GeneralUser (Inherits from User)

### Attributes:
- **- reminderList: List<Reminder>** (private) - User's active reminders

### Methods:
- **+ querySystemMetrics(query: MetricQuery): MetricData** (public) - Query read-only metrics
- **+ manageSchedule(scheduleRequest: ScheduleRequest): ScheduleResult** (public) - Manage calendar
- **+ setReminder(reminder: Reminder): Boolean** (public) - Set timed reminders

---

## 4. NLPEngine

### Attributes:
- **- model: LanguageModel** (private) - The NLP model instance
- **- confidenceThreshold: Float** (private) - Minimum confidence (default 0.5)
- **- accuracyTarget: Float** (private) - Target accuracy (0.85)

### Methods:
- **+ parseCommand(input: String): ParsedIntent** (public) - Parse natural language input
- **+ extractEntities(input: String): List<Entity>** (public) - Extract entities from input
- **+ calculateConfidence(intent: Intent): Float** (public) - Calculate confidence score
- **- preprocessText(input: String): String** (private) - Preprocess input text
- **- tokenize(input: String): List<Token>** (private) - Tokenize input

---

## 5. ParsedIntent

### Attributes:
- **- intent: Intent** (private) - The identified intent
- **- entities: List<Entity>** (private) - Extracted entities
- **- confidence: Float** (private) - Confidence score (0-1)
- **- timestamp: DateTime** (private) - When parsed

### Methods:
- **+ getIntent(): Intent** (public) - Get intent
- **+ getEntities(): List<Entity>** (public) - Get entities
- **+ getConfidence(): Float** (public) - Get confidence score
- **+ isAboveThreshold(threshold: Float): Boolean** (public) - Check if confidence meets threshold
- **+ toString(): String** (public) - String representation

---

## 6. ContextManager

### Attributes:
- **- contextStore: Map<String, MessageHistory>** (private) - User ID to message history
- **- maxContextSize: Integer** (private) - Maximum context size (3 messages)

### Methods:
- **+ getContext(userId: String): MessageHistory** (public) - Retrieve user's context
- **+ updateContext(userId: String, message: Message): void** (public) - Update context
- **+ resolveReference(userId: String, reference: String): Entity** (public) - Resolve contextual references (e.g., "its")
- **- pruneOldMessages(history: MessageHistory): void** (private) - Keep only last 3 messages

---

## 7. TaskExecutor

### Attributes:
- **- scriptRegistry: ScriptRegistry** (private) - Registry of available scripts
- **- executionQueue: Queue<Task>** (private) - Task queue
- **- maxConcurrentTasks: Integer** (private) - Maximum concurrent tasks (50)

### Methods:
- **+ executeTask(task: Task): ExecutionResult** (public) - Execute a task
- **+ requiresConfirmation(task: Task): Boolean** (public) - Check if confirmation needed
- **+ executeReadOnlyTask(task: Task): ExecutionResult** (public) - Execute read-only tasks
- **+ executeWriteTask(task: Task, confirmed: Boolean): ExecutionResult** (public) - Execute write tasks
- **- invokeScript(script: Script, params: Map<String, Object>): Result** (private) - Invoke external script
- **- maskSensitiveData(output: String): String** (private) - Mask passwords, keys, etc.

---

## 8. Script

### Attributes:
- **- scriptId: String** (private) - Unique script identifier
- **- name: String** (private) - Script name
- **- filePath: String** (private) - Path to script file
- **- language: ScriptLanguage** (private) - Python, Bash, etc.
- **- mappedIntent: Intent** (private) - Associated intent
- **- parameters: List<Parameter>** (private) - Expected parameters
- **- isReadOnly: Boolean** (private) - Whether script modifies state
- **- registeredBy: Administrator** (private) - Admin who registered it

### Methods:
- **+ execute(params: Map<String, Object>): ScriptResult** (public) - Execute the script
- **+ validate(): Boolean** (public) - Validate script integrity
- **+ getScriptId(): String** (public) - Get script ID
- **+ isReadOnly(): Boolean** (public) - Check if read-only
- **- parseParameters(params: Map<String, Object>): String[]** (private) - Parse parameters for execution

---

## 9. ScriptRegistry

### Attributes:
- **- scripts: Map<String, Script>** (private) - Script ID to Script mapping
- **- intentMapping: Map<Intent, List<Script>>** (private) - Intent to scripts mapping

### Methods:
- **+ registerScript(script: Script): Boolean** (public) - Register new script
- **+ getScript(scriptId: String): Script** (public) - Retrieve script by ID
- **+ findScriptsByIntent(intent: Intent): List<Script>** (public) - Find scripts for intent
- **+ unregisterScript(scriptId: String): Boolean** (public) - Remove script
- **- validateUnique(script: Script): Boolean** (private) - Ensure no duplicates

---

## 10. AuditLogger

### Attributes:
- **- logDatabase: Database** (private) - Database connection
- **- logFormat: LogFormat** (private) - Log entry format

### Methods:
- **+ logExecution(entry: AuditEntry): Boolean** (public) - Log execution to database
- **+ retrieveLogs(filter: LogFilter): List<AuditEntry>** (public) - Retrieve logs
- **- formatEntry(entry: AuditEntry): String** (private) - Format log entry
- **- persistToDatabase(entry: AuditEntry): Boolean** (private) - Persist to DB

---

## 11. AuditEntry

### Attributes:
- **- entryId: String** (private) - Unique entry ID
- **- userId: String** (private) - User who executed
- **- command: String** (private) - Command executed
- **- timestamp: DateTime** (private) - When executed
- **- result: ExecutionResult** (private) - Execution result
- **- executionTime: Long** (private) - Time taken (ms)

### Methods:
- **+ getEntryId(): String** (public) - Get entry ID
- **+ toJSON(): String** (public) - Convert to JSON
- **+ toString(): String** (public) - String representation

---

## 12. SelfCorrectionEngine

### Attributes:
- **- errorDatabase: Database** (private) - Error logs database
- **- analysisModel: MLModel** (private) - ML model for error analysis
- **- suggestionCache: Map<String, List<Suggestion>>** (private) - Cached suggestions

### Methods:
- **+ analyzeError(error: ExecutionError): ErrorAnalysis** (public) - Analyze error and suggest fix
- **+ storeError(error: ExecutionError): Boolean** (public) - Store error in database
- **+ getSuggestions(errorPattern: String): List<Suggestion>** (public) - Get suggestions
- **- parseErrorLog(log: String): ErrorPattern** (private) - Parse error log
- **- generateSuggestion(pattern: ErrorPattern): Suggestion** (private) - Generate fix suggestion

---

## 13. CalendarIntegration

### Attributes:
- **- apiClient: CalendarAPIClient** (private) - Calendar API client
- **- apiKey: String** (private) - API authentication key
- **- defaultTimezone: String** (private) - Default timezone

### Methods:
- **+ checkAvailability(request: AvailabilityRequest): AvailabilityResult** (public) - Check calendar availability
- **+ bookMeeting(request: MeetingRequest): MeetingResult** (public) - Book meeting slot
- **+ setReminder(reminder: Reminder): Boolean** (public) - Set calendar reminder
- **- parseNaturalLanguageTime(input: String): DateTime** (private) - Parse time from NL
- **- validateTimeSlot(slot: TimeSlot): Boolean** (private) - Validate time slot

---

## 14. AuthenticationService

### Attributes:
- **- identityProvider: IdentityProviderAPI** (private) - External identity provider
- **- sessionManager: SessionManager** (private) - Manages user sessions
- **- tokenExpiry: Integer** (private) - Token expiry time (seconds)

### Methods:
- **+ authenticate(credentials: Credentials): AuthToken** (public) - Authenticate user
- **+ validateToken(token: String): Boolean** (public) - Validate auth token
- **+ refreshToken(token: String): AuthToken** (public) - Refresh expired token
- **+ logout(userId: String): Boolean** (public) - Logout user
- **- hashPassword(password: String): String** (private) - Hash password
- **- generateToken(userId: String): String** (private) - Generate auth token

---

## 15. ExecutionResult

### Attributes:
- **- success: Boolean** (private) - Whether execution succeeded
- **- output: String** (private) - Execution output (masked if sensitive)
- **- error: ExecutionError** (private) - Error details (if failed)
- **- executionTime: Long** (private) - Time taken (ms)
- **- timestamp: DateTime** (private) - When executed

### Methods:
- **+ isSuccess(): Boolean** (public) - Check if successful
- **+ getOutput(): String** (public) - Get output
- **+ getError(): ExecutionError** (public) - Get error details
- **+ toJSON(): String** (public) - Convert to JSON

---

## 16. ConfirmationPrompt

### Attributes:
- **- promptId: String** (private) - Unique prompt ID
- **- message: String** (private) - Confirmation message
- **- task: Task** (private) - Associated task
- **- userId: String** (private) - User being prompted
- **- expiryTime: DateTime** (private) - When prompt expires
- **- confirmed: Boolean** (private) - Whether confirmed

### Methods:
- **+ display(): String** (public) - Display prompt to user
- **+ confirm(): Boolean** (public) - Confirm action
- **+ cancel(): Boolean** (public) - Cancel action
- **+ isExpired(): Boolean** (public) - Check if expired

---

## Supporting Enums and Value Objects:

### UserRole (Enum)
- GENERAL
- ADMIN

### Intent (Enum)
- CHECK_STATUS
- RESTART_SERVICE
- QUERY_METRICS
- SCHEDULE_MEETING
- SET_REMINDER
- REGISTER_SCRIPT
- UNKNOWN

### ScriptLanguage (Enum)
- PYTHON
- BASH
- SHELL

### Entity (Value Object)
- name: String
- value: String
- type: EntityType (SERVER, SERVICE, TIME, etc.)
