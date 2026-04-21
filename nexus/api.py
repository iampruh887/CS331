"""
Unified API Layer for the Nexus Intelligent Chatbot System.

Provides REST API endpoints that orchestrate all components including:
- Command execution with NLP parsing
- Confirmation handling for write actions
- Script registration and management
- Audit log retrieval
- Calendar operations
"""

import logging
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, EmailStr
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import Nexus components
from nexus.config import config
from nexus.database import db, DatabaseError
from nexus.models import (
    Intent, Entity, EntityType, User, UserRole, Task, ExecutionResult,
    ConfirmationPrompt, Script, ScriptLanguage, Parameter, AuditEntry,
    LogFilter, Message, MessageHistory
)
from nexus.nlp_engine import NLPEngine
from nexus.context_manager import ContextManager
from nexus.task_executor import TaskExecutor, TaskExecutorError
from nexus.script_registry import ScriptRegistry, ScriptRegistryError
from nexus.audit_logger import AuditLogger, AuditLoggerError
from nexus.calendar_integration import CalendarIntegration
from auth.auth import get_current_user, create_access_token, verify_password
from auth.models import TokenData, Token, UserLogin, User as AuthUser

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
nlp_engine = NLPEngine()
context_manager = ContextManager()
script_registry = ScriptRegistry()
task_executor = TaskExecutor(script_registry=script_registry)
audit_logger = AuditLogger()
calendar_integration = CalendarIntegration()

# Request/Response Models

class CommandRequest(BaseModel):
    """Request model for command execution."""
    command: str = Field(..., min_length=1, max_length=4000, description="Natural language command")
    
    class Config:
        json_schema_extra = {
            "example": {
                "command": "Check the status of the nginx service on web-server-01"
            }
        }


class CommandResponse(BaseModel):
    """Response model for command execution."""
    intent: str
    confidence: float
    result: Dict[str, Any]
    confirmation_prompt: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "intent": "check_status",
                "confidence": 0.85,
                "result": {
                    "success": True,
                    "output": "Service is running"
                }
            }
        }


class ConfirmationRequest(BaseModel):
    """Request model for confirmation."""
    confirmed: bool = Field(..., description="Whether to confirm or cancel the action")
    
    class Config:
        json_schema_extra = {
            "example": {
                "confirmed": True
            }
        }


class ScriptRegistrationRequest(BaseModel):
    """Request model for script registration."""
    script_id: str = Field(..., description="Unique script identifier")
    name: str = Field(..., description="Human-readable script name")
    file_path: str = Field(..., description="Path to script file")
    language: str = Field(..., description="Script language (python or bash)")
    mapped_intents: List[str] = Field(..., description="List of intent values this script handles")
    parameters: List[Dict[str, Any]] = Field(default_factory=list, description="Script parameters")
    is_read_only: bool = Field(..., description="Whether this is a read-only action")
    
    class Config:
        json_schema_extra = {
            "example": {
                "script_id": "check_nginx_status",
                "name": "Check Nginx Status",
                "file_path": "/scripts/check_nginx.py",
                "language": "python",
                "mapped_intents": ["check_status"],
                "parameters": [
                    {
                        "name": "service",
                        "type": "string",
                        "required": True,
                        "description": "Service name"
                    }
                ],
                "is_read_only": True
            }
        }


class ScriptResponse(BaseModel):
    """Response model for script information."""
    script_id: str
    name: str
    file_path: str
    language: str
    mapped_intents: List[str]
    parameters: List[Dict[str, Any]]
    is_read_only: bool
    registered_by: str
    created_at: str


class AuditLogResponse(BaseModel):
    """Response model for audit log entry."""
    entry_id: str
    user_id: str
    user_email: str
    command: str
    intent: str
    success: bool
    output: Optional[str]
    error: Optional[str]
    execution_time_ms: int
    timestamp: str


class MeetingScheduleRequest(BaseModel):
    """Request model for meeting scheduling."""
    title: str = Field(..., description="Meeting title")
    start_time: str = Field(..., description="Start time (ISO format)")
    duration_minutes: int = Field(..., description="Duration in minutes")
    attendees: List[str] = Field(default_factory=list, description="Attendee emails")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Team Standup",
                "start_time": "2024-03-26T10:00:00",
                "duration_minutes": 30,
                "attendees": ["team@example.com"]
            }
        }


class ReminderRequest(BaseModel):
    """Request model for reminder creation."""
    title: str = Field(..., description="Reminder title")
    reminder_time: str = Field(..., description="Reminder time (ISO format)")
    description: Optional[str] = Field(None, description="Reminder description")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Team Meeting",
                "reminder_time": "2024-03-26T10:00:00",
                "description": "Don't forget the team standup"
            }
        }


class ErrorResponse(BaseModel):
    """Response model for errors."""
    error: str
    detail: Optional[str] = None
    request_id: Optional[str] = None


# Middleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Startup
    logger.info("Initializing Nexus API...")
    db.initialize_schema()
    logger.info("Database schema initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Nexus API...")
    task_executor.shutdown()
    logger.info("Task executor shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Nexus Intelligent Chatbot API",
    description="Unified API for the Nexus Intelligent Chatbot System",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "NEXUS_ALLOWED_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173,http://localhost:3000",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    logger.info(f"[{request_id}] {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    logger.info(f"[{request_id}] Response status: {response.status_code}")
    
    return response


# Error handling middleware
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    
    logger.error(f"[{request_id}] Unhandled exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "request_id": request_id
        }
    )


# Helper functions

async def get_current_user_with_role(token: str = Depends(get_current_user)) -> User:
    """Get current user with role information."""
    # In a real implementation, this would fetch user role from database
    # For now, we'll create a User object from the token
    return User(
        user_id=token.email,
        email=token.email,
        role=UserRole.GENERAL,  # Default role
        is_active=True
    )


async def require_admin(user: User = Depends(get_current_user_with_role)) -> User:
    """Require admin role for endpoint."""
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


# Health check endpoint

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Nexus API",
        "version": "1.0.0"
    }


# Command execution endpoints

@app.post("/api/v1/command", response_model=CommandResponse)
async def execute_command(
    request: CommandRequest,
    user: User = Depends(get_current_user_with_role)
):
    """
    Execute a natural language command.
    
    Orchestrates the full flow:
    1. Parse command with NLP Engine
    2. Enrich with context
    3. Execute task
    4. Log execution
    
    For write actions, returns a confirmation prompt instead of executing.
    """
    request_id = str(uuid.uuid4())
    
    try:
        logger.info(f"[{request_id}] Processing command: {request.command}")
        
        # Parse command with NLP Engine
        parsed_intent = await nlp_engine.parse_command(request.command, user)
        
        logger.info(f"[{request_id}] Parsed intent: {parsed_intent.intent.value} (confidence: {parsed_intent.confidence})")
        
        # Check confidence threshold
        if parsed_intent.confidence < config.CONFIDENCE_THRESHOLD:
            fallback_msg = nlp_engine.get_low_confidence_fallback(parsed_intent.intent)
            return CommandResponse(
                intent=parsed_intent.intent.value,
                confidence=parsed_intent.confidence,
                result={
                    "success": False,
                    "output": fallback_msg,
                    "error": "Low confidence parsing"
                }
            )
        
        # Update context
        message = Message(
            text=request.command,
            intent=parsed_intent.intent,
            entities=parsed_intent.entities,
            timestamp=datetime.utcnow()
        )
        context_manager.update_context(user.user_id, message)
        
        # Find script for intent
        scripts = script_registry.find_scripts_by_intent(parsed_intent.intent)
        if not scripts:
            return CommandResponse(
                intent=parsed_intent.intent.value,
                confidence=parsed_intent.confidence,
                result={
                    "success": False,
                    "output": f"No script registered for intent: {parsed_intent.intent.value}",
                    "error": "No matching script"
                }
            )
        
        # Use first matching script
        script = scripts[0]
        
        # Create task
        task = Task(
            intent=parsed_intent.intent,
            entities=parsed_intent.entities,
            script_id=script.script_id,
            parameters={},
            is_write_action=not script.is_read_only
        )
        
        # Execute task
        execution_result = task_executor.execute_task(task, user)
        
        # Log execution
        audit_entry = audit_logger.create_audit_entry(
            user_id=user.user_id,
            user_email=user.email,
            command=request.command,
            intent=parsed_intent.intent,
            result=execution_result
        )
        await audit_logger.log_execution(audit_entry)
        
        # Check if confirmation prompt was generated
        confirmation_prompt = None
        if task.is_write_action and "Confirmation required" in execution_result.output:
            # Extract prompt ID from output (would be set by task executor)
            confirmation_prompt = {
                "message": execution_result.output,
                "prompt_id": "pending"  # Would be set by task executor
            }
        
        return CommandResponse(
            intent=parsed_intent.intent.value,
            confidence=parsed_intent.confidence,
            result={
                "success": execution_result.success,
                "output": execution_result.output,
                "error": execution_result.error,
                "execution_time_ms": execution_result.execution_time_ms
            },
            confirmation_prompt=confirmation_prompt
        )
        
    except Exception as e:
        logger.error(f"[{request_id}] Error executing command: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/api/v1/confirm/{prompt_id}", response_model=CommandResponse)
async def confirm_action(
    prompt_id: str,
    request: ConfirmationRequest,
    user: User = Depends(get_current_user_with_role)
):
    """
    Confirm or cancel a write action.
    
    Args:
        prompt_id: Confirmation prompt ID
        request: Confirmation request with confirmed flag
        user: Authenticated user
    """
    request_id = str(uuid.uuid4())
    
    try:
        logger.info(f"[{request_id}] Processing confirmation for prompt: {prompt_id}")
        
        # Execute with confirmation
        execution_result = task_executor.confirm_and_execute(
            prompt_id=prompt_id,
            confirmed=request.confirmed,
            user=user
        )
        
        # Log confirmation
        audit_entry = audit_logger.create_audit_entry(
            user_id=user.user_id,
            user_email=user.email,
            command=f"Confirmation: {prompt_id}",
            intent=Intent.UNKNOWN,
            result=execution_result
        )
        await audit_logger.log_execution(audit_entry)
        
        return CommandResponse(
            intent="confirmation",
            confidence=1.0,
            result={
                "success": execution_result.success,
                "output": execution_result.output,
                "error": execution_result.error,
                "execution_time_ms": execution_result.execution_time_ms
            }
        )
        
    except TaskExecutorError as e:
        logger.error(f"[{request_id}] Task executor error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"[{request_id}] Error confirming action: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Script management endpoints

@app.post("/api/v1/scripts", response_model=Dict[str, Any])
async def register_script(
    request: ScriptRegistrationRequest,
    admin_user: User = Depends(require_admin)
):
    """
    Register a new script (admin only).
    
    Args:
        request: Script registration request
        admin_user: Authenticated admin user
    """
    request_id = str(uuid.uuid4())
    
    try:
        logger.info(f"[{request_id}] Registering script: {request.script_id}")
        
        # Validate language
        try:
            language = ScriptLanguage(request.language.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid language: {request.language}. Must be 'python' or 'bash'"
            )
        
        # Validate intents
        try:
            mapped_intents = [Intent(intent) for intent in request.mapped_intents]
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid intent: {str(e)}"
            )
        
        # Create parameters
        parameters = [
            Parameter(
                name=p.get("name"),
                type=p.get("type", "string"),
                required=p.get("required", False),
                description=p.get("description", "")
            )
            for p in request.parameters
        ]
        
        # Create script object
        script = Script(
            script_id=request.script_id,
            name=request.name,
            file_path=request.file_path,
            language=language,
            mapped_intents=mapped_intents,
            parameters=parameters,
            is_read_only=request.is_read_only,
            registered_by=admin_user.email,
            created_at=datetime.utcnow()
        )
        
        # Register script
        script_registry.register_script(script, admin_user)
        
        logger.info(f"[{request_id}] Script registered successfully: {request.script_id}")
        
        return {
            "success": True,
            "script_id": request.script_id,
            "message": f"Script '{request.name}' registered successfully"
        }
        
    except ScriptRegistryError as e:
        logger.error(f"[{request_id}] Script registry error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"[{request_id}] Error registering script: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/api/v1/scripts", response_model=List[ScriptResponse])
async def list_scripts(
    user: User = Depends(get_current_user_with_role)
):
    """
    List all registered scripts.
    
    Args:
        user: Authenticated user
    """
    try:
        scripts = script_registry.list_all_scripts()
        
        return [
            ScriptResponse(
                script_id=s.script_id,
                name=s.name,
                file_path=s.file_path,
                language=s.language.value,
                mapped_intents=[i.value for i in s.mapped_intents],
                parameters=[
                    {
                        "name": p.name,
                        "type": p.type,
                        "required": p.required,
                        "description": p.description
                    }
                    for p in s.parameters
                ],
                is_read_only=s.is_read_only,
                registered_by=s.registered_by,
                created_at=s.created_at.isoformat()
            )
            for s in scripts
        ]
        
    except Exception as e:
        logger.error(f"Error listing scripts: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Audit log endpoints

@app.get("/api/v1/audit", response_model=List[AuditLogResponse])
async def get_audit_logs(
    user_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    intent: Optional[str] = None,
    admin_user: User = Depends(require_admin)
):
    """
    Retrieve audit logs (admin only).
    
    Supports filtering by user, date range, and intent.
    
    Args:
        user_id: Filter by user ID
        start_date: Filter by start date (ISO format)
        end_date: Filter by end date (ISO format)
        intent: Filter by intent
        admin_user: Authenticated admin user
    """
    request_id = str(uuid.uuid4())
    
    try:
        logger.info(f"[{request_id}] Retrieving audit logs")
        
        # Parse dates
        start_dt = None
        end_dt = None
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid start_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
                )
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid end_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
                )
        
        # Parse intent
        intent_enum = None
        if intent:
            try:
                intent_enum = Intent(intent)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid intent: {intent}"
                )
        
        # Create filter
        log_filter = LogFilter(
            user_id=user_id,
            start_date=start_dt,
            end_date=end_dt,
            intent=intent_enum
        )
        
        # Retrieve logs
        entries = await audit_logger.retrieve_logs(log_filter)
        
        logger.info(f"[{request_id}] Retrieved {len(entries)} audit log entries")
        
        return [
            AuditLogResponse(
                entry_id=e.entry_id,
                user_id=e.user_id,
                user_email=e.user_email,
                command=e.command,
                intent=e.intent.value,
                success=e.result.success,
                output=e.result.output,
                error=e.result.error,
                execution_time_ms=e.execution_time_ms,
                timestamp=e.timestamp.isoformat()
            )
            for e in entries
        ]
        
    except AuditLoggerError as e:
        logger.error(f"[{request_id}] Audit logger error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"[{request_id}] Error retrieving audit logs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Calendar endpoints

@app.post("/api/v1/calendar/schedule", response_model=Dict[str, Any])
async def schedule_meeting(
    request: MeetingScheduleRequest,
    user: User = Depends(get_current_user_with_role)
):
    """
    Schedule a meeting.
    
    Args:
        request: Meeting scheduling request
        user: Authenticated user
    """
    request_id = str(uuid.uuid4())
    
    try:
        logger.info(f"[{request_id}] Scheduling meeting: {request.title}")
        
        # Parse start time
        try:
            start_time = datetime.fromisoformat(request.start_time)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_time format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
            )
        
        # Create meeting request
        from nexus.models import MeetingRequest as MeetingRequestModel
        meeting_request = MeetingRequestModel(
            user_email=user.email,
            title=request.title,
            start_time=start_time,
            duration_minutes=request.duration_minutes,
            attendees=request.attendees
        )
        
        # Schedule meeting
        result = calendar_integration.book_meeting(meeting_request)
        
        logger.info(f"[{request_id}] Meeting scheduled successfully")
        
        return {
            "success": result.success,
            "meeting_id": result.meeting_id,
            "confirmation_message": result.confirmation_message
        }
        
    except Exception as e:
        logger.error(f"[{request_id}] Error scheduling meeting: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/api/v1/calendar/reminder", response_model=Dict[str, Any])
async def create_reminder(
    request: ReminderRequest,
    user: User = Depends(get_current_user_with_role)
):
    """
    Create a reminder.
    
    Args:
        request: Reminder creation request
        user: Authenticated user
    """
    request_id = str(uuid.uuid4())
    
    try:
        logger.info(f"[{request_id}] Creating reminder: {request.title}")
        
        # Parse reminder time
        try:
            reminder_time = datetime.fromisoformat(request.reminder_time)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reminder_time format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
            )
        
        # Create reminder object
        from nexus.models import Reminder as ReminderModel
        reminder = ReminderModel(
            user_email=user.email,
            title=request.title,
            reminder_time=reminder_time,
            description=request.description
        )
        
        # Create reminder
        success = calendar_integration.set_reminder(reminder)
        
        logger.info(f"[{request_id}] Reminder created successfully")
        
        return {
            "success": success,
            "message": f"Reminder '{request.title}' created successfully"
        }
        
    except Exception as e:
        logger.error(f"[{request_id}] Error creating reminder: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Root endpoint

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Nexus Intelligent Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "health": "GET /health",
            "command": "POST /api/v1/command",
            "confirm": "POST /api/v1/confirm/{prompt_id}",
            "scripts": {
                "register": "POST /api/v1/scripts",
                "list": "GET /api/v1/scripts"
            },
            "audit": "GET /api/v1/audit",
            "calendar": {
                "schedule": "POST /api/v1/calendar/schedule",
                "reminder": "POST /api/v1/calendar/reminder"
            }
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
