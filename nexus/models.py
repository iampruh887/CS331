"""
Data models for the Nexus Intelligent Chatbot System.

This module contains all data classes used throughout the system including
intents, entities, tasks, execution results, scripts, audit entries, and more.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any


# Enums

class Intent(Enum):
    """Intent types identified by the NLP Engine."""
    CHECK_STATUS = "check_status"
    RESTART_SERVICE = "restart_service"
    QUERY_METRICS = "query_metrics"
    SCHEDULE_MEETING = "schedule_meeting"
    SET_REMINDER = "set_reminder"
    REGISTER_SCRIPT = "register_script"
    UNKNOWN = "unknown"


class EntityType(Enum):
    """Entity types extracted from user commands."""
    SERVER = "server"
    SERVICE = "service"
    TIME = "time"
    METRIC = "metric"
    SCRIPT_NAME = "script_name"
    USER_EMAIL = "user_email"


class ScriptLanguage(Enum):
    """Supported script languages."""
    PYTHON = "python"
    BASH = "bash"


class UserRole(Enum):
    """User roles for authorization."""
    GENERAL = "GENERAL"
    ADMIN = "ADMIN"


# NLP and Intent Models

@dataclass
class Entity:
    """Extracted entity from user command."""
    entity_type: EntityType
    value: str
    confidence: float = 1.0


@dataclass
class ParsedIntent:
    """Result of NLP parsing."""
    intent: Intent
    entities: List[Entity]
    confidence: float
    raw_command: str


# Context Management Models

@dataclass
class Message:
    """Individual message in conversation history."""
    text: str
    intent: Intent
    entities: List[Entity]
    timestamp: datetime


@dataclass
class MessageHistory:
    """Conversation history for a user (max 3 messages)."""
    user_id: str
    messages: List[Message] = field(default_factory=list)
    
    def add_message(self, message: Message) -> None:
        """Add message and maintain max size of 3."""
        self.messages.append(message)
        if len(self.messages) > 3:
            self.messages = self.messages[-3:]


# Script Registry Models

@dataclass
class Parameter:
    """Script parameter definition."""
    name: str
    type: str  # string, int, bool
    required: bool
    description: str


@dataclass
class Script:
    """Registered script metadata."""
    script_id: str
    name: str
    file_path: str
    language: ScriptLanguage
    mapped_intents: List[Intent]
    parameters: List[Parameter]
    is_read_only: bool
    registered_by: str  # Admin email
    created_at: datetime = field(default_factory=datetime.utcnow)


# Task Execution Models

@dataclass
class Task:
    """Task to be executed."""
    intent: Intent
    entities: List[Entity]
    script_id: str
    parameters: Dict[str, Any]
    is_write_action: bool


@dataclass
class ExecutionResult:
    """Result of task execution."""
    success: bool
    output: str  # Masked if sensitive
    error: Optional[str] = None
    execution_time_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ConfirmationPrompt:
    """Confirmation request for write actions."""
    prompt_id: str
    message: str
    task: Task
    user_id: str
    expiry_time: datetime
    confirmed: Optional[bool] = None


# Audit Logging Models

@dataclass
class AuditEntry:
    """Immutable audit log entry."""
    entry_id: str  # UUID
    user_id: str
    user_email: str
    command: str
    intent: Intent
    result: ExecutionResult
    timestamp: datetime
    execution_time_ms: int


@dataclass
class LogFilter:
    """Filter criteria for audit log queries."""
    user_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    intent: Optional[Intent] = None
    success_only: Optional[bool] = None


# Error Handling Models

@dataclass
class ExecutionError:
    """Error from task execution."""
    error_id: str
    task: Task
    error_message: str
    stack_trace: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ErrorPattern:
    """Known error pattern for self-correction."""
    pattern_id: str
    pattern_regex: str
    description: str
    common_causes: List[str]
    suggested_fixes: List[str]


@dataclass
class ErrorAnalysis:
    """Analysis result from Self-Correction Engine."""
    error_id: str
    pattern_matched: Optional[ErrorPattern]
    suggestions: List[str]
    confidence: float


# Calendar Integration Models

@dataclass
class TimeSlot:
    """Available time slot."""
    start: datetime
    end: datetime


@dataclass
class AvailabilityRequest:
    """Request to check calendar availability."""
    user_email: str
    start_time: datetime
    end_time: datetime
    duration_minutes: int


@dataclass
class AvailabilityResult:
    """Result of availability check."""
    available_slots: List[TimeSlot]


@dataclass
class MeetingRequest:
    """Request to book a meeting."""
    user_email: str
    title: str
    start_time: datetime
    duration_minutes: int
    attendees: List[str]


@dataclass
class MeetingResult:
    """Result of meeting booking."""
    success: bool
    meeting_id: str
    confirmation_message: str


@dataclass
class Reminder:
    """Reminder to be created."""
    user_email: str
    title: str
    reminder_time: datetime
    description: Optional[str] = None


# User Models

@dataclass
class User:
    """User information."""
    user_id: str
    email: str
    role: UserRole
    is_active: bool = True
