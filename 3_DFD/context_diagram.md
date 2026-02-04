# Context Diagram (Level 0 DFD) - Nexus Intelligent Chatbot System

## Overview
The Context Diagram shows the Nexus system as a single process with external entities and data flows.

## External Entities:
1. **General User** - Non-technical staff
2. **Administrator** - Technical users with elevated privileges
3. **Identity Provider** - Authentication service
4. **Calendar API** - External scheduling service
5. **Infra/Script Engine** - Infrastructure execution engine
6. **Database/Audit Log** - Persistent storage system

## Data Flows:

### From Users to Nexus System:
- Natural Language Commands
- Authentication Credentials
- Script Registration Requests (Admin only)
- Confirmation Responses

### From Nexus System to Users:
- Execution Results
- System Metrics
- Confirmation Prompts
- Fallback Messages
- Error Reports with Suggested Fixes
- Scheduled Meeting Confirmations
- Reminder Notifications

### Between Nexus and External Systems:

**Identity Provider:**
- To: Authentication Request (User credentials)
- From: Authentication Token/Response

**Calendar API:**
- To: Schedule/Query Request (meeting times, availability checks)
- From: Calendar Data (availability, booking confirmations)

**Infra/Script Engine:**
- To: Execution Commands (with parameters)
- From: Execution Results/System Metrics

**Database/Audit Log:**
- To: Log Entries (User ID, Command, Timestamp, Result)
- From: Historical Data/Context (last 3 messages)

## Key Features Shown:
- Bidirectional communication with users
- Integration with external authentication
- Calendar scheduling capabilities
- Infrastructure command execution
- Audit logging and contextual memory
