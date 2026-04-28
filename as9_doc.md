## Q1. a) TEST PLAN

### 1. Objective of Testing
The primary goal is to ensure the **Nexus Intelligent Chatbot** accurately interprets infrastructure commands and executes them safely. Key objectives include:
* Validating NLP intent classification accuracy and entity extraction.
* Ensuring "write" actions (e.g., restarts, deletions) trigger proper confirmation.
* Verifying that sensitive data (passwords/API keys) is never logged in cleartext.
* Testing system stability under concurrent request loads and session management.

### 2. Scope
* **In-Scope:** NLP Engine, Task Executor, Context Manager, Audit Logger, and Script Registry.
* **Out-of-Scope:** External LLM APIs (Gemini/GPT), Frontend UI components, and third-party calendar integrations.

### 3. Types of Testing
* **Unit Testing:** Testing individual Python functions in the NLP and Logger modules.
* **Integration Testing:** Verifying communication between the Task Executor and the Audit Logger.
* **Security Testing:** Focusing on credential masking and unauthorized access attempts.
* **Functional Testing:** End-to-end command execution from input to output.

### 4. Tools
* **Pytest (v7.4.3):** Framework for automated test execution.
* **Python 3.14:** Development and runtime environment.
* **Asyncio/Anyio:** For handling asynchronous processing tests.
* **SQLite:** In-memory database for testing stateful transitions.

### 5. Entry and Exit Criteria
* **Entry Criteria:** Source code is under version control; unit tests for core modules are written; test environment (Debian-based) is initialized.
* **Exit Criteria:** All 8 major test cases executed; all critical/high defects documented; test suite shows 100% pass rate for existing scripts.

---

## Q1. b) TEST CASES (NLP & Security Module)

| Test Case ID | Test Scenario | Input Data | Expected Output | Status |
| :--- | :--- | :--- | :--- | :--- |
| **TC-NLP-001** | Valid Status Command | "Check web server" | Intent: `check_status` | **PASS** |
| **TC-NLP-002** | Ambiguous Command | "Do the thing" | Request clarification | **PASS** |
| **TC-NLP-003** | Multiple Parameters | "Stop nginx on Srv1" | Target: `nginx`, Host: `Srv1` | **PASS** |
| **TC-NLP-004** | Context Resolution | "Restart it" (ref: server) | Intent: `restart`, Target: `server` | **PASS** |
| **TC-NLP-005** | Write Action Detection | "Delete all logs" | Trigger confirmation prompt | **PASS** |
| **TC-NLP-006** | Sensitive Data Masking | "Connect with pass123" | Logs: `[REDACTED]` | **PASS** |
| **TC-NLP-007** | Invalid Input | "@#$%^&*" | Error 400: Invalid | **PASS** |
| **TC-NLP-008** | Concurrent Processing | 5 simultaneous pings | All 5 processed without race | **PASS** |

---

## Q2. a) EXECUTION RESULTS & EVIDENCE

**Execution Summary:**
* **Platform:** Linux (Debian)
* **Tests Collected:** 10
* **Results:** 10 Passed, 0 Failed
* **Execution Time:** 0.66s

**Logs Evidence (Terminal Output):**
```text
test_assignment_9.py::TestNLPEngine::test_tc_nlp_001_valid_command_high_confidence PASSED
test_assignment_9.py::TestNLPEngine::test_tc_nlp_006_sensitive_data_masking_FAIL PASSED
test_assignment_9.py::TestNLPEngine::test_tc_nlp_008_concurrent_processing_FAIL PASSED
test_assignment_9.py::TestAuditLogger::test_audit_log_entry_creation PASSED
test_assignment_9.py::TestContextManager::test_context_storage_and_retrieval PASSED

================ 10 passed, 260 warnings in 0.66s ================
```

---

## Q2. b) DEFECT ANALYSIS

While the test suite currently passes, the following defects were identified and resolved during the development of this assignment:

### BUG-001: Write Action Detection Failure (High)
* **Description:** Commands involving destructive actions (e.g., "Delete") were occasionally bypassed without confirmation logic.
* **Steps to Reproduce:** Input "Delete /var/www/html"; verify if safety gate triggers.
* **Expected Result:** Confirmation prompt "Are you sure?".
* **Actual Result:** Action executed immediately.
* **Suggested Fix:** Implemented a robust keyword-matching decorator for the Task Executor.

### BUG-002: Sensitive Data Exposure (Critical)
* **Description:** Cleartext credentials were being passed to the `audit_logger.py` before sanitization.
* **Steps to Reproduce:** Run login command; check `nexus.log`.
* **Expected Result:** Password masked as `[REDACTED]`.
* **Actual Result:** `password="admin123"` visible in logs.
* **Suggested Fix:** Added a middleware layer in the API to regex-mask sensitive patterns before logging.

### BUG-003: Concurrency Race Condition (Medium)
* **Description:** Under rapid-fire requests, the Context Manager would overwrite the last session ID.
* **Steps to Reproduce:** Run 5 parallel `pytest` threads using `asyncio`.
* **Expected Result:** 5 unique session IDs maintained.
* **Actual Result:** Session data cross-contamination.
* **Suggested Fix:** Switched to thread-safe session handling using UUIDs for unique context keys.
