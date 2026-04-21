# CS 331 (Software Engineering Lab) — Assignment 7  
## Q1: Business Logic Layer (BLL) Modules in the Project and Their Interaction with the Presentation Layer  
---

## 1) Objective
A Business Logic Layer (BLL) contains the core rules/processing of the application and sits between:
- **Presentation Layer (UI)**: what the user interacts with
- **Data Access Layer (DB/storage)**: persistence and retrieval of data

---

## 2) High-level Architecture in This Repo (Relevant to BLL)
The system is split into services/modules such as:

- **Frontend (Presentation Layer)**: `client/` (React)
- **Backend APIs (BLL entry points)**:
  - `auth/` → Authentication API (FastAPI)
  - `chat/` → Chat API (FastAPI)
  - `model/` → NLP / parsing / agent execution logic (Python)

The BLL is primarily implemented in the Python backend modules that enforce rules, validate inputs, manage tokens/roles, and orchestrate the “chat → AI processing → response” flow.

---

## 3) Core Functional Modules of the BLL

### Module A — Authentication & Identity (BLL)
**Location:** `auth/`  
**Purpose (Business Logic):**
- User registration and login
- Password verification and hashing
- JWT creation and validation
- Role handling (e.g., `GENERAL`, `ADMIN`)

**Key business rules implemented:**
- Prevent registering an already-existing email (reject with 400)
- Reject invalid credentials (401)
- Issue time-limited JWT tokens (configured expiration)
- Provide `/me` endpoint to fetch current user identity/role based on token

**Key API endpoints (BLL interface):**
- `POST /register`
- `POST /login`
- `GET /me`


---

### Module B — Chat Request Handling / Response Generation (BLL)
**Location:** `chat/chat_api.py`  
**Purpose (Business Logic):**
- Accept a user chat message
- Validate request payload rules (min/max length)
- Enforce server configuration (API key presence)
- Generate a reply by calling an external LLM endpoint (Gemini in current code)
- Normalize/parse the provider response into a clean reply string

**Key business rules implemented:**
- Reject if `GEMINI_API_KEY` is missing (500)
- Validate message length via Pydantic model constraints
- Fail safely on provider HTTP/network errors and return meaningful errors
- Extract reply text from provider response structure

**Key API endpoint (BLL interface):**
- `POST /chat`

---

### Module C — NLP / Parsing / Orchestration Layer (BLL)
**Location:** `model/main.py`  
**Purpose (Business Logic):**
- Run the agent/runner pipeline to interpret a user query
- Maintain session context (in-memory session service)
- Orchestrate tool/function calls and collect the final text response
- Log tool usage and results (auditing/trace)

**Key business rules implemented:**
- Create/maintain session IDs
- Choose the “tool name” used (if any) for logging
- Ensure some response is returned even if the agent yields nothing


> Note: In this repo, the *Chat API* currently calls Gemini directly. The *Model module* demonstrates a richer “agent runner” orchestration pattern. Both represent BLL behavior; depending on deployment, one can be the primary execution path.

---

## 4) Interaction With the Presentation Layer (React UI)

### Presentation Layer (UI) Components
**Location:** `client/src/`  
Key files:
- `client/src/App.jsx` (main UI logic: login/register, message composer, calling backend)
- `client/src/main.jsx` (React bootstrap)
- `client/src/App.css` (styling, not BLL)

---

## 5) End-to-End Interaction Flows (UI ↔ BLL)

### Flow 1 — User Registration (UI → Auth BLL)
1. User selects **Register** mode in the UI and inputs email/password.
2. React calls:
   - `POST /register` on the Auth API
3. Auth BLL:
   - checks if user exists (`user_exists`)
   - creates user record (`create_user`)
   - returns user profile info (email, role, active)

**Result:** account created and UI can proceed to login.

---

### Flow 2 — Login + Session Setup (UI → Auth BLL)
1. User enters credentials in UI and clicks login.
2. React calls:
   - `POST /login`
3. Auth BLL validates password and returns `access_token`.
4. React then calls:
   - `GET /me` with header `Authorization: Bearer <token>`
5. Auth BLL returns the authenticated user profile (email/role).
6. UI stores token + user info in `localStorage` and app state.

**Business logic demonstrated:**
- Authentication gatekeeping and identity propagation to UI.

---

### Flow 3 — Chat Submission (UI → Chat BLL → Provider → UI)
1. User types a message in the chat input and submits.
2. React calls:
   - `POST /chat` with JSON `{ "message": "..." }`
3. Chat BLL:
   - validates message length
   - checks `GEMINI_API_KEY`
   - calls Gemini endpoint
   - extracts reply text and returns `{ reply: "..." }`
4. UI appends assistant reply to message list and renders it.

**Business logic demonstrated:**
- Controlled interaction with external LLM + error handling + structured response.

---

## 6) Summary Table: BLL Modules vs UI Touchpoints

| BLL Module | Repo Location | UI Component(s) | Interaction Mechanism |
|---|---|---|---|
| Authentication & Identity | `auth/` | `client/src/App.jsx` | REST calls: `/register`, `/login`, `/me` |
| Chat API / Response Generation | `chat/` | `client/src/App.jsx` | REST call: `/chat` |
| NLP / Parsing / Orchestration | `model/` | (indirect / backend use) | Runner-based orchestration (backend execution path) |

---

## 7) Conclusion
- The project contains concrete **BLL modules** implemented in Python (FastAPI services and agent/orchestration logic).
- The **Presentation Layer** in React (`client/src/App.jsx`) interacts with the BLL via **REST APIs**:
  - Auth endpoints for registration/login/profile
  - Chat endpoint for submitting prompts and receiving responses
- These interactions demonstrate the intended layering: UI delegates rules/processing to the BLL, and the BLL enforces business rules and returns structured outcomes.

---