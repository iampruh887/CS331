# CS 331 (Software Engineering Lab) — Assignment 7  
## Q2: Business Rules, Validation Logic, and Data Transformation (BLL)  
---

## A) Business Rules Implementation

Business rules are the explicit conditions and policies that the application enforces to ensure correct behavior (e.g., access control, error conditions, safe execution constraints). In this project, business rules are primarily implemented inside the backend services (FastAPI) and the orchestration/agent layer.

### 1) Authentication & Identity Module (`auth/`)
**Where implemented:** `auth/main.py` (and helper modules imported by it)

**Key rules enforced:**
- **Unique identity rule:** A user email cannot be registered twice.  
  - Implemented by checking `user_exists(user.email)` and rejecting with HTTP **400** (“Email already registered”).
- **Credential correctness rule:** A user can only log in if password verification passes.  
  - Implemented by verifying the password hash (`verify_password(...)`); invalid credentials return HTTP **401**.
- **Session/token rule:** Access tokens are time-limited and created using configured expiry.  
  - Implemented via `create_access_token(..., expires_delta=...)`.
- **Identity retrieval rule:** `/me` must return the authenticated user (and fail if user is not found).  
  - Uses `get_current_user` dependency (token-based identity extraction) and returns **404** if DB user doesn’t exist.

**Why this is business logic:** it defines who may access the system and under what conditions (authorization/authentication policy).

---

### 2) Chat Module (`chat/`)
**Where implemented:** `chat/chat_api.py`

**Key rules enforced:**
- **System configuration rule:** Chat cannot run unless `GEMINI_API_KEY` is configured on server.  
  - If missing, endpoint returns HTTP **500** (“not configured”).
- **Provider-call safety rules:**
  - Network/provider errors (HTTPError/URLError) are caught and returned as HTTP **502**.
  - Empty model response is treated as an error (HTTP **502**).
- **Output formatting rule:** Only the relevant text parts are extracted from the provider response and returned as a clean `reply` string.  
  - Implemented in `_extract_reply(...)`.

**Why this is business logic:** it enforces safe/consistent behavior for generating assistant responses and defines error conditions.

---

### 3) NLP / Orchestration Module (`model/`)
**Where implemented:** `model/main.py`

**Key rules enforced:**
- **Session management rule:** Each query is associated with a session (and attempts to create it before running).  
- **Fallback rule:** If the agent returns no response, return a safe default (“No response received…”).  
- **Audit/logging rule:** The system records which tool/function was used (if any) and logs input/output.

**Why this is business logic:** it defines how user intent is processed and how the system behaves under incomplete/edge scenarios.

---

## B) Validation Logic Implemented

Validation logic ensures incoming data is correct and in an acceptable format *before* the system processes it further. This project uses validation in multiple layers:

### 1) API request validation (Chat API)
**Where:** `chat/chat_api.py`

- The request body is defined using Pydantic:
  - `ChatRequest.message: str = Field(min_length=1, max_length=4000)`
- This ensures:
  - message cannot be empty
  - message cannot exceed 4000 characters
  - wrong types / malformed JSON are rejected by FastAPI/Pydantic automatically

**Benefit:** prevents invalid/huge payloads from reaching the AI call logic.

---

### 2) Authentication input validation (Auth API)
**Where:** `auth/main.py` (via request models such as `UserCreate`, `UserLogin` imported in the file)

- Auth endpoints accept typed models, so incorrect input shapes are rejected automatically.
- Additionally, there is *rule-level validation*:
  - duplicate email check (`user_exists`)
  - incorrect password check (`verify_password`)

**Benefit:** prevents inconsistent identity state and blocks unauthorized logins.

---

### 3) Environment/config validation (Chat API)
**Where:** `chat/chat_api.py`

- Explicit validation that `GEMINI_API_KEY` exists before serving chat requests.

**Benefit:** avoids “silent failures” and makes runtime misconfiguration visible.

---

## C) Data Transformation for UI Consumption

Data transformation is the conversion of internal/data-layer formats (DB objects, provider payloads, internal models) into a UI-friendly response format (usually stable JSON structures with only needed fields).

### 1) Database → API Response Transformation (Auth)
**Where:** `auth/main.py`

- The database user record (`db_user`) contains internal fields such as:
  - `hashed_password` (sensitive)
  - internal DB identifiers, timestamps, etc. (not always needed by UI)
- The API transforms DB records into a safe response model, returning only:
  - `email`
  - `is_active`
  - `role`

**Example transformation behavior:**
- DB user → `User(...)` response model
- Sensitive fields are not returned to the client.

**Why it matters:** UI needs a clean profile object; it must never receive hashed passwords or internal DB data.

---

### 2) External Provider Payload → Clean Chat Response (Chat)
**Where:** `chat/chat_api.py`

- Gemini API returns a nested structure (`candidates -> content -> parts -> text`).
- The system transforms that structure into a single string `reply`:
  - `_extract_reply(api_response)` collects `text` parts and joins them
- Then it returns a stable response format:
  - `ChatResponse(reply=<string>)`

**Why it matters:** The React UI should not need to understand Gemini’s raw schema; it only consumes `{ reply }`.

---

### 3) Backend JSON → UI State Transformation (React)
**Where:** `client/src/App.jsx` (presentation layer handling)

- The frontend converts backend responses into UI-specific state:
  - token + user profile → stored in `localStorage` and React state
  - chat replies → appended to `messages[]` with fields like `id`, `role`, `text`, `createdAt`

**Why it matters:** UI rendering needs message objects with metadata, not raw API responses.

---

## Conclusion
- **Business rules** are implemented mainly in backend services (`auth/`, `chat/`, and `model/`) as explicit conditions, access policies, error handling, and orchestration rules.
- **Validation logic** is implemented using FastAPI + Pydantic constraints and additional checks (duplicate users, credential verification, required API keys).
- **Data transformation** is handled by converting:
  - DB records → safe user profile DTOs (excluding sensitive fields)
  - Provider payloads → a stable `{ reply: string }` API response
  - API responses → UI-friendly React state structures

---
