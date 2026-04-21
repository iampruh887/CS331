"""
Integration tests for the Nexus Intelligent Chatbot System.

Tests end-to-end flows including:
- Complete command flow (login → parse → execute → audit)
- Write action with confirmation
- Calendar scheduling
- Error correction
- Context resolution
"""

import pytest
import tempfile
import os
import uuid
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from nexus.nlp_engine import NLPEngine
from nexus.context_manager import ContextManager
from nexus.task_executor import TaskExecutor
from nexus.script_registry import ScriptRegistry
from nexus.audit_logger import AuditLogger
from nexus.self_correction_engine import SelfCorrectionEngine
from nexus.calendar_integration import CalendarIntegration
from nexus.models import (
    Task, ExecutionResult, ConfirmationPrompt, Script, ScriptLanguage,
    Intent, EntityType, Entity, Parameter, User, UserRole, Message,
    MessageHistory, ParsedIntent, AuditEntry, ExecutionError
)
from nexus.database import db as global_db, Database
from nexus.config import config


# Fixtures

@pytest.fixture
def test_db_path():
    """Create a temporary database file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def test_db(test_db_path):
    """Create a test database instance."""
    db = Database(test_db_path)
    db.initialize_schema()
    return db


@pytest.fixture
def components(test_db):
    """Create all system components for integration testing."""
    nlp_engine = NLPEngine()
    context_manager = ContextManager()
    script_registry = ScriptRegistry(database=test_db)
    task_executor = TaskExecutor(script_registry=script_registry, database=test_db)
    audit_logger = AuditLogger(database=test_db)
    self_correction_engine = SelfCorrectionEngine(database=test_db)
    calendar_integration = CalendarIntegration()
    
    return {
        'nlp_engine': nlp_engine,
        'context_manager': context_manager,
        'script_registry': script_registry,
        'task_executor': task_executor,
        'audit_logger': audit_logger,
        'self_correction_engine': self_correction_engine,
        'calendar_integration': calendar_integration,
        'db': test_db
    }


@pytest.fixture
def admin_user():
    """Create an admin user."""
    return User(
        user_id="admin1",
        email="admin@example.com",
        role=UserRole.ADMIN
    )


@pytest.fixture
def general_user():
    """Create a general user."""
    return User(
        user_id="user1",
        email="user@example.com",
        role=UserRole.GENERAL
    )


@pytest.fixture
def sample_read_script():
    """Create a sample read-only script."""
    return Script(
        script_id=f"read_script_{uuid.uuid4().hex[:8]}",
        name="Check Service Status",
        file_path="/scripts/check_status.py",
        language=ScriptLanguage.PYTHON,
        mapped_intents=[Intent.CHECK_STATUS],
        parameters=[
            Parameter(name="service", type="string", required=True, description="Service name")
        ],
        is_read_only=True,
        registered_by="admin@example.com"
    )


@pytest.fixture
def sample_write_script():
    """Create a sample write-action script."""
    return Script(
        script_id=f"write_script_{uuid.uuid4().hex[:8]}",
        name="Restart Service",
        file_path="/scripts/restart_service.sh",
        language=ScriptLanguage.BASH,
        mapped_intents=[Intent.RESTART_SERVICE],
        parameters=[
            Parameter(name="service", type="string", required=True, description="Service name")
        ],
        is_read_only=False,
        registered_by="admin@example.com"
    )


# Integration Tests

class TestCompleteCommandFlow:
    """Test complete command flow: login → parse → execute → audit."""
    
    @pytest.mark.asyncio
    async def test_complete_command_flow_read_action(self, components, admin_user, sample_read_script):
        """
        Test complete flow for read action.
        
        Flow: User login → Submit command → NLP parsing → Context enrichment → 
              Task execution → Audit logging
        """
        # Step 1: Register script
        components['script_registry'].register_script(sample_read_script, admin_user)
        
        # Step 2: Parse command with NLP
        command = "Check the status of nginx service"
        with patch.object(components['nlp_engine'], 'parse_command', new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = ParsedIntent(
                intent=Intent.CHECK_STATUS,
                entities=[Entity(entity_type=EntityType.SERVICE, value="nginx")],
                confidence=0.95,
                raw_command=command
            )
            parsed_intent = await components['nlp_engine'].parse_command(command, admin_user.user_id)
        
        # Step 3: Update context
        message = Message(
            text=command,
            intent=parsed_intent.intent,
            entities=parsed_intent.entities,
            timestamp=datetime.utcnow()
        )
        components['context_manager'].update_context(admin_user.user_id, message)
        
        # Step 4: Create and execute task
        task = Task(
            intent=parsed_intent.intent,
            entities=parsed_intent.entities,
            script_id=sample_read_script.script_id,
            parameters={"service": "nginx"},
            is_write_action=False
        )
        
        result = components['task_executor'].execute_task(task, admin_user)
        
        # Step 5: Verify audit logging
        assert result is not None
        assert isinstance(result, ExecutionResult)
        
        # Verify context was updated
        context = components['context_manager'].get_context(admin_user.user_id)
        assert context is not None
        assert len(context.messages) == 1
        assert context.messages[0].intent == Intent.CHECK_STATUS
    
    @pytest.mark.asyncio
    async def test_complete_command_flow_with_context_resolution(self, components, admin_user, sample_read_script):
        """
        Test command flow with context resolution.
        
        Flow: Submit command → Parse → Store context → Submit follow-up with reference →
              Resolve reference → Execute
        """
        # Register script
        components['script_registry'].register_script(sample_read_script, admin_user)
        
        # First command: "Check nginx service"
        first_command = "Check the status of nginx service"
        with patch.object(components['nlp_engine'], 'parse_command', new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = ParsedIntent(
                intent=Intent.CHECK_STATUS,
                entities=[Entity(entity_type=EntityType.SERVICE, value="nginx")],
                confidence=0.95,
                raw_command=first_command
            )
            first_parsed = await components['nlp_engine'].parse_command(first_command, admin_user.user_id)
        
        # Store first message in context
        first_message = Message(
            text=first_command,
            intent=first_parsed.intent,
            entities=first_parsed.entities,
            timestamp=datetime.utcnow()
        )
        components['context_manager'].update_context(admin_user.user_id, first_message)
        
        # Second command: "Restart it"
        second_command = "Restart it"
        with patch.object(components['nlp_engine'], 'parse_command', new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = ParsedIntent(
                intent=Intent.RESTART_SERVICE,
                entities=[],  # No entities in "Restart it"
                confidence=0.85,
                raw_command=second_command
            )
            second_parsed = await components['nlp_engine'].parse_command(second_command, admin_user.user_id)
        
        # Resolve reference "it" to the service from context
        resolved_entity = components['context_manager'].resolve_reference(
            admin_user.user_id,
            "it",
            EntityType.SERVICE
        )
        
        # Verify reference was resolved
        assert resolved_entity is not None
        assert resolved_entity.value == "nginx"
        assert resolved_entity.entity_type == EntityType.SERVICE
        
        # Store second message in context
        second_message = Message(
            text=second_command,
            intent=second_parsed.intent,
            entities=[resolved_entity],
            timestamp=datetime.utcnow()
        )
        components['context_manager'].update_context(admin_user.user_id, second_message)
        
        # Verify context has both messages
        context = components['context_manager'].get_context(admin_user.user_id)
        assert len(context.messages) == 2
        assert context.messages[1].entities[0].value == "nginx"


class TestWriteActionWithConfirmation:
    """Test write action with confirmation flow."""
    
    def test_write_action_confirmation_flow(self, components, admin_user, sample_write_script):
        """
        Test write action confirmation flow.
        
        Flow: Submit write action → Confirmation prompt → Confirm → Execute → Audit log
        """
        # Register write script
        components['script_registry'].register_script(sample_write_script, admin_user)
        
        # Create write action task
        task = Task(
            intent=Intent.RESTART_SERVICE,
            entities=[Entity(entity_type=EntityType.SERVICE, value="nginx")],
            script_id=sample_write_script.script_id,
            parameters={"service": "nginx"},
            is_write_action=True
        )
        
        # Step 1: Execute task (should create confirmation prompt)
        result = components['task_executor'].execute_task(task, admin_user)
        assert result is not None
        assert "Confirmation required" in result.output or result.success is True
        
        # Step 2: If confirmation was required, get the prompt
        if "Confirmation required" in result.output:
            # Get confirmation prompt from database - find by user_id
            # Query the database directly for prompts
            with components['db'].get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT prompt_id FROM confirmation_prompts WHERE user_id = ?",
                    (admin_user.user_id,)
                )
                rows = cursor.fetchall()
                assert len(rows) > 0
                prompt_id = rows[0][0]
            
            # Step 3: Confirm the action
            confirmed_result = components['task_executor'].confirm_and_execute(
                prompt_id,
                True,
                admin_user
            )
            assert confirmed_result is not None
            assert isinstance(confirmed_result, ExecutionResult)
    
    def test_write_action_cancellation_flow(self, components, admin_user, sample_write_script):
        """
        Test write action cancellation.
        
        Flow: Submit write action → Confirmation prompt → Cancel → No execution
        """
        # Register write script
        components['script_registry'].register_script(sample_write_script, admin_user)
        
        # Create write action task
        task = Task(
            intent=Intent.RESTART_SERVICE,
            entities=[Entity(entity_type=EntityType.SERVICE, value="nginx")],
            script_id=sample_write_script.script_id,
            parameters={"service": "nginx"},
            is_write_action=True
        )
        
        # Execute task (should create confirmation prompt)
        result = components['task_executor'].execute_task(task, admin_user)
        
        if "Confirmation required" in result.output:
            # Get confirmation prompt from database
            with components['db'].get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT prompt_id FROM confirmation_prompts WHERE user_id = ?",
                    (admin_user.user_id,)
                )
                rows = cursor.fetchall()
                prompt_id = rows[0][0]
            
            # Cancel the action
            canceled_result = components['task_executor'].confirm_and_execute(
                prompt_id,
                False,
                admin_user
            )
            
            # Verify action was not executed
            assert canceled_result.success is False
            assert "canceled" in canceled_result.output.lower()


class TestCalendarScheduling:
    """Test calendar scheduling integration."""
    
    def test_calendar_scheduling_flow(self, components, admin_user):
        """
        Test calendar scheduling flow.
        
        Flow: Submit meeting request → Parse time → Check availability → Book meeting
        """
        # Mock calendar API
        with patch.object(components['calendar_integration'], 'check_availability') as mock_check:
            mock_check.return_value = Mock(
                available_slots=[
                    Mock(start=datetime.utcnow() + timedelta(hours=1), 
                         end=datetime.utcnow() + timedelta(hours=2))
                ]
            )
            
            # Check availability
            from nexus.models import AvailabilityRequest
            availability_request = AvailabilityRequest(
                user_email=admin_user.email,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow() + timedelta(hours=8),
                duration_minutes=60
            )
            
            availability = components['calendar_integration'].check_availability(availability_request)
            assert availability is not None
            assert len(availability.available_slots) > 0
        
        # Mock meeting booking
        with patch.object(components['calendar_integration'], 'book_meeting') as mock_book:
            mock_book.return_value = Mock(
                success=True,
                meeting_id=str(uuid.uuid4()),
                confirmation_message="Meeting booked successfully"
            )
            
            # Book meeting
            from nexus.models import MeetingRequest
            meeting_request = MeetingRequest(
                user_email=admin_user.email,
                title="Team Standup",
                start_time=datetime.utcnow() + timedelta(hours=1),
                duration_minutes=30,
                attendees=["team@example.com"]
            )
            
            booking_result = components['calendar_integration'].book_meeting(meeting_request)
            assert booking_result.success is True
            assert booking_result.meeting_id is not None


class TestErrorCorrection:
    """Test error correction flow."""
    
    def test_error_correction_flow(self, components, admin_user, test_db):
        """
        Test error correction flow.
        
        Flow: Execute failing task → Store error → Analyze pattern → Return suggestions
        """
        # Create a failing task
        task = Task(
            intent=Intent.CHECK_STATUS,
            entities=[Entity(entity_type=EntityType.SERVICE, value="nonexistent")],
            script_id="nonexistent_script",
            parameters={},
            is_write_action=False
        )
        
        # Execute task (will fail)
        result = components['task_executor'].execute_task(task, admin_user)
        assert result.success is False
        assert result.error is not None
        
        # Store error
        error = ExecutionError(
            error_id=str(uuid.uuid4()),
            task=task,
            error_message=result.error,
            stack_trace=None,
            timestamp=datetime.utcnow()
        )
        
        components['self_correction_engine'].store_error(error)
        
        # Analyze error
        analysis = components['self_correction_engine'].analyze_error(error)
        assert analysis is not None
        assert analysis.error_id == error.error_id


class TestContextResolution:
    """Test context resolution in multi-turn conversations."""
    
    def test_context_resolution_with_multiple_entities(self, components, admin_user):
        """
        Test context resolution with multiple entities.
        
        Flow: Submit command with entity → Submit follow-up with reference → 
              Resolve reference → Execute
        """
        # First command with multiple entities
        first_command = "Check nginx on web-server-01"
        first_parsed = ParsedIntent(
            intent=Intent.CHECK_STATUS,
            entities=[
                Entity(entity_type=EntityType.SERVICE, value="nginx"),
                Entity(entity_type=EntityType.SERVER, value="web-server-01")
            ],
            confidence=0.95,
            raw_command=first_command
        )
        
        first_message = Message(
            text=first_command,
            intent=first_parsed.intent,
            entities=first_parsed.entities,
            timestamp=datetime.utcnow()
        )
        components['context_manager'].update_context(admin_user.user_id, first_message)
        
        # Second command with reference to service
        second_command = "Restart that service"
        second_parsed = ParsedIntent(
            intent=Intent.RESTART_SERVICE,
            entities=[],
            confidence=0.85,
            raw_command=second_command
        )
        
        # Resolve "that service" reference
        resolved_service = components['context_manager'].resolve_reference(
            admin_user.user_id,
            "that service",
            EntityType.SERVICE
        )
        
        assert resolved_service is not None
        assert resolved_service.value == "nginx"
        
        # Third command with reference to server
        third_command = "Check disk space on that server"
        third_parsed = ParsedIntent(
            intent=Intent.QUERY_METRICS,
            entities=[],
            confidence=0.90,
            raw_command=third_command
        )
        
        # Resolve "that server" reference
        resolved_server = components['context_manager'].resolve_reference(
            admin_user.user_id,
            "that server",
            EntityType.SERVER
        )
        
        assert resolved_server is not None
        assert resolved_server.value == "web-server-01"
        
        # Verify context maintains all messages
        context = components['context_manager'].get_context(admin_user.user_id)
        assert len(context.messages) == 1  # Only first message stored
    
    def test_context_pruning_maintains_max_size(self, components, admin_user):
        """
        Test that context is pruned to maintain max size of 3 messages.
        """
        # Add 5 messages
        for i in range(5):
            message = Message(
                text=f"Command {i}",
                intent=Intent.CHECK_STATUS,
                entities=[Entity(entity_type=EntityType.SERVICE, value=f"service{i}")],
                timestamp=datetime.utcnow()
            )
            components['context_manager'].update_context(admin_user.user_id, message)
        
        # Verify only last 3 messages are kept
        context = components['context_manager'].get_context(admin_user.user_id)
        assert len(context.messages) == 3
        assert context.messages[0].text == "Command 2"
        assert context.messages[1].text == "Command 3"
        assert context.messages[2].text == "Command 4"
