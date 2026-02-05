# Level 1 DFD - Nexus Intelligent Chatbot System

## Processes:

### P1: Authenticate User
- **Input:** User credentials from General User/Administrator
- **Output:** Authentication success/failure to users
- **Data Stores:** D1 (User Profiles) - read/write
- **External:** Identity Provider (authentication)
- **Function:** Validates user identity and retrieves user profile

### P2: Parse Intent & Entities (NLP)
- **Input:** Natural language commands from users
- **Output:** Intent + Entities OR Fallback response
- **Function:** Uses NLP engine to extract intent and entities with 85% accuracy
- **Condition:** If confidence < 50%, provides fallback response

### P3: Consult Contextual Memory
- **Input:** Intent + Entities from P2
- **Output:** Enriched intent to P4 or Schedule request to P6
- **Data Stores:** D2 (Contextual Memory) - read
- **Function:** Retrieves last 3 messages to understand context (e.g., "its" refers to Server A)

### P4: Execute Task
- **Input:** Enriched intent from P3, confirmation from Admin
- **Output:** Masked results to users, execution details to P5, errors to P8
- **Data Stores:** D4 (Script Registry) - read
- **External:** Infra/Script Engine
- **Function:** 
  - Looks up appropriate script from registry
  - Requests confirmation for write actions (FR-06)
  - Executes commands via infrastructure engine
  - Masks sensitive data (NFR-04)

### P5: Log Execution
- **Input:** Execution details from P4
- **Output:** Log entries to D3, context updates to D2
- **Data Stores:** D3 (Audit Log) - write, D2 (Contextual Memory) - write
- **Function:** Records User ID, Command, Timestamp, Result (FR-07)

### P6: Manage Schedule/Reminders
- **Input:** Schedule request from P3
- **Output:** Confirmation/Reminder notifications to users
- **External:** Calendar API
- **Function:** Handles meeting scheduling and reminder management (FR-08, FR-09)

### P7: Register External Script
- **Input:** Script + metadata from Administrator
- **Output:** Registration status to Administrator
- **Data Stores:** D4 (Script Registry) - write
- **Function:** Registers new executable scripts (FR-04)

### P8: Trigger Self-Correction
- **Input:** Error details from P4
- **Output:** Suggested fixes to Administrator
- **Data Stores:** D5 (Error Logs) - read/write
- **Function:** Analyzes error logs and suggests fixes (Novelty feature)

## Data Stores:

### D1: User Profiles
- **Content:** User credentials, authentication tokens, user roles
- **Access:** P1 (read/write)
- **Purpose:** User authentication and authorization

### D2: Contextual Memory
- **Content:** Last 3 messages per user session
- **Access:** P3 (read), P5 (write)
- **Purpose:** Enable context-aware command interpretation (Novelty feature)

### D3: Audit Log
- **Content:** User ID, Command, Timestamp, Execution Result
- **Access:** P5 (write)
- **Purpose:** Compliance and audit trail (FR-07)

### D4: Script Registry
- **Content:** Registered scripts with metadata (intent mapping, parameters)
- **Access:** P4 (read), P7 (write)
- **Purpose:** Plugin architecture for task execution (FR-04)

### D5: Error Logs
- **Content:** Error messages, stack traces, failure patterns
- **Access:** P8 (read/write)
- **Purpose:** Self-correction mechanism (Novelty feature)

## External Entities:

1. **General User** - Non-technical users
2. **Administrator** - Technical users with elevated privileges
3. **Identity Provider** - External authentication service
4. **Calendar API** - Scheduling service (Google Calendar)
5. **Infra/Script Engine** - Infrastructure command execution engine

## Key Data Flows:

- **Authentication Flow:** User → P1 → Identity Provider → D1
- **Command Execution Flow:** User → P2 → P3 → P4 → Infra/Script Engine
- **Logging Flow:** P4 → P5 → D3
- **Context Management:** P5 → D2 → P3
- **Error Handling:** P4 → P8 → D5 → User
