"""
Unit tests for the Task Executor component.

Tests task execution, confirmation handling, and sensitive data masking.
"""

import pytest
import tempfile
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from nexus.task_executor import TaskExecutor, TaskExecutorError
from nexus.models import (
    Task, ExecutionResult, ConfirmationPrompt, Script, ScriptLanguage,
    Intent, EntityType, Entity, Parameter, User, UserRole
)
from nexus.script_registry import ScriptRegistry
from nexus.database import db as global_db, Database
from nexus.config import config


# Create a temporary database for testing
@pytest.fixture
def test_db_path():
    """Create a temporary database file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        path = f.name
    yield path
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def executor(test_db_path):
    """Create a TaskExecutor instance with test database."""
    test_db = Database(test_db_path)
    test_db.initialize_schema()
    # Create ScriptRegistry with the test database
    script_registry = ScriptRegistry(database=test_db)
    # Clear any existing scripts to avoid test interference
    return TaskExecutor(script_registry=script_registry, database=test_db, max_concurrent_tasks=10)


@pytest.fixture
def admin_user():
    """Create an admin user for authorization tests."""
    return User(
        user_id="admin1",
        email="admin@example.com",
        role=UserRole.ADMIN
    )


@pytest.fixture
def general_user():
    """Create a general user for authorization tests."""
    return User(
        user_id="user1",
        email="user@example.com",
        role=UserRole.GENERAL
    )


@pytest.fixture
def sample_read_script():
    """Create a sample read-only script for testing."""
    return Script(
        script_id=f"read_script_{uuid.uuid4().hex[:8]}",
        name="Read Only Script",
        file_path="/scripts/read_script.py",
        language=ScriptLanguage.PYTHON,
        mapped_intents=[Intent.CHECK_STATUS],
        parameters=[
            Parameter(name="server", type="string", required=True, description="Server name")
        ],
        is_read_only=True,
        registered_by="admin@example.com"
    )


@pytest.fixture
def sample_write_script():
    """Create a sample write-action script for testing."""
    return Script(
        script_id=f"write_script_{uuid.uuid4().hex[:8]}",
        name="Write Action Script",
        file_path="/scripts/write_script.sh",
        language=ScriptLanguage.BASH,
        mapped_intents=[Intent.RESTART_SERVICE],
        parameters=[
            Parameter(name="service", type="string", required=True, description="Service name")
        ],
        is_read_only=False,
        registered_by="admin@example.com"
    )


class TestTaskExecutorConfirmation:
    """Tests for confirmation handling in Task Executor."""
    
    def test_requires_confirmation_for_write_action(self, executor):
        """Write actions should require confirmation."""
        task = Task(
            intent=Intent.RESTART_SERVICE,
            entities=[],
            script_id="write_script_001",
            parameters={},
            is_write_action=True
        )
        assert executor.requires_confirmation(task) is True
    
    def test_requires_no_confirmation_for_read_action(self, executor):
        """Read actions should not require confirmation."""
        task = Task(
            intent=Intent.CHECK_STATUS,
            entities=[],
            script_id="read_script_001",
            parameters={},
            is_write_action=False
        )
        assert executor.requires_confirmation(task) is False
    
    def test_execute_with_confirmation_creates_prompt(self, executor, admin_user, sample_write_script):
        """Execute with confirmation should create a prompt."""
        # Register the script first using executor's registry
        executor.script_registry.register_script(sample_write_script, admin_user)
        
        task = Task(
            intent=Intent.RESTART_SERVICE,
            entities=[],
            script_id="write_script_001",
            parameters={},
            is_write_action=True
        )
        
        prompt = executor.execute_with_confirmation(task, admin_user)
        assert prompt is not None
        assert prompt.prompt_id is not None
        assert prompt.message is not None
        assert prompt.task == task
        assert prompt.user_id == admin_user.user_id
        assert prompt.confirmed is None
    
    def test_confirm_and_execute_confirmed(self, executor, admin_user, sample_write_script):
        """Execute task after confirmation."""
        # Register the script first using executor's registry
        executor.script_registry.register_script(sample_write_script, admin_user)
        
        task = Task(
            intent=Intent.RESTART_SERVICE,
            entities=[],
            script_id="write_script_001",
            parameters={},
            is_write_action=True
        )
        
        # Create confirmation prompt
        prompt = executor.execute_with_confirmation(task, admin_user)
        
        # Execute with confirmation
        result = executor.confirm_and_execute(prompt.prompt_id, True, admin_user)
        assert result is not None
        assert isinstance(result, ExecutionResult)
    
    def test_confirm_and_execute_canceled(self, executor, admin_user, sample_write_script):
        """Cancel task execution."""
        # Register the script first using executor's registry
        executor.script_registry.register_script(sample_write_script, admin_user)
        
        task = Task(
            intent=Intent.RESTART_SERVICE,
            entities=[],
            script_id="write_script_001",
            parameters={},
            is_write_action=True
        )
        
        # Create confirmation prompt
        prompt = executor.execute_with_confirmation(task, admin_user)
        
        # Cancel the action
        result = executor.confirm_and_execute(prompt.prompt_id, False, admin_user)
        assert result.success is False
        assert "canceled" in result.output.lower()
    
    def test_confirm_and_execute_expired_prompt_raises_error(self, executor, admin_user, sample_write_script):
        """Expired confirmation prompt should raise error."""
        # Register the script first using executor's registry
        executor.script_registry.register_script(sample_write_script, admin_user)
        
        task = Task(
            intent=Intent.RESTART_SERVICE,
            entities=[],
            script_id="write_script_001",
            parameters={},
            is_write_action=True
        )
        
        # Create confirmation prompt with past expiry
        prompt_id = str(uuid.uuid4())
        expiry_time = datetime.utcnow() - timedelta(minutes=1)
        
        task_json = executor._serialize_task(task)
        executor.db.insert_confirmation_prompt(
            prompt_id=prompt_id,
            message="Test",
            task_json=task_json,
            user_id=admin_user.user_id,
            expiry_time=expiry_time
        )
        
        with pytest.raises(TaskExecutorError) as exc_info:
            executor.confirm_and_execute(prompt_id, True, admin_user)
        assert "expired" in str(exc_info.value).lower()
    
    def test_confirm_and_execute_unauthorized_user_raises_error(self, executor, admin_user, general_user, sample_write_script):
        """Unauthorized user should not be able to confirm."""
        # Register the script first using executor's registry
        executor.script_registry.register_script(sample_write_script, admin_user)
        
        task = Task(
            intent=Intent.RESTART_SERVICE,
            entities=[],
            script_id="write_script_001",
            parameters={},
            is_write_action=True
        )
        
        # Create confirmation prompt for admin_user
        prompt = executor.execute_with_confirmation(task, admin_user)
        
        # Try to confirm as general_user
        with pytest.raises(TaskExecutorError) as exc_info:
            executor.confirm_and_execute(prompt.prompt_id, True, general_user)
        assert "authorized" in str(exc_info.value).lower()


class TestTaskExecutorSensitiveDataMasking:
    """Tests for sensitive data masking in Task Executor."""
    
    def test_mask_password_in_output(self, executor):
        """Password should be masked in output."""
        output = "Password: mysecretpassword123"
        masked = executor._mask_sensitive_data(output)
        assert "[PASSWORD_MASKED]" in masked
        assert "mysecretpassword123" not in masked
    
    def test_mask_api_key_in_output(self, executor):
        """API key should be masked in output."""
        output = "API Key: sk-1234567890abcdef"
        masked = executor._mask_sensitive_data(output)
        assert "[API_KEY_MASKED]" in masked
        assert "sk-1234567890abcdef" not in masked
    
    def test_mask_token_in_output(self, executor):
        """Token should be masked in output."""
        output = "Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        masked = executor._mask_sensitive_data(output)
        assert "[TOKEN_MASKED]" in masked
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in masked
    
    def test_mask_secret_in_output(self, executor):
        """Secret should be masked in output."""
        output = "Secret: mysupersecretvalue"
        masked = executor._mask_sensitive_data(output)
        assert "[SECRET_MASKED]" in masked
        assert "mysupersecretvalue" not in masked
    
    def test_clean_output_unchanged(self, executor):
        """Clean output without sensitive data should be unchanged."""
        output = "Server status: OK\nCPU: 45%\nMemory: 60%"
        masked = executor._mask_sensitive_data(output)
        assert masked == output
    
    def test_mask_multiple_sensitive_patterns(self, executor):
        """Multiple sensitive patterns should all be masked."""
        output = "Password: secret123\nAPI Key: sk-abcdef123456\nToken: bearer-token-xyz"
        masked = executor._mask_sensitive_data(output)
        assert "[PASSWORD_MASKED]" in masked
        assert "[API_KEY_MASKED]" in masked
        assert "[TOKEN_MASKED]" in masked


class TestTaskExecutorScriptExecution:
    """Tests for script execution in Task Executor."""
    
    def test_invoke_script_python(self, executor, admin_user, sample_read_script):
        """Execute a Python script."""
        # Register the script first using executor's registry
        executor.script_registry.register_script(sample_read_script, admin_user)
        
        # Create a temporary Python script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('#!/usr/bin/env python3\nprint("Hello from Python script")\n')
            f.flush()
            sample_read_script.file_path = f.name
        
        try:
            params = {}
            output = executor._invoke_script(sample_read_script, params)
            assert "Hello from Python script" in output
        finally:
            if os.path.exists(f.name):
                os.unlink(f.name)
    
    def test_invoke_script_bash(self, executor, admin_user, sample_write_script):
        """Execute a Bash script."""
        # Register the script first using executor's registry
        executor.script_registry.register_script(sample_write_script, admin_user)
        
        # Create a temporary Bash script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write('#!/bin/bash\necho "Hello from Bash script"\n')
            f.flush()
            sample_write_script.file_path = f.name
        
        try:
            params = {}
            output = executor._invoke_script(sample_write_script, params)
            assert "Hello from Bash script" in output
        finally:
            if os.path.exists(f.name):
                os.unlink(f.name)
    
    def test_invoke_script_with_parameters(self, executor, admin_user, sample_read_script):
        """Execute a script with parameters."""
        # Register the script first using executor's registry
        executor.script_registry.register_script(sample_read_script, admin_user)
        
        # Create a temporary Python script that accepts parameters
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('#!/usr/bin/env python3\nimport sys\nimport argparse\nparser = argparse.ArgumentParser()\nparser.add_argument("--server", required=True)\nargs = parser.parse_args()\nprint(f"Server: {args.server}")\n')
            f.flush()
            sample_read_script.file_path = f.name
        
        try:
            params = {"server": "web-server-01"}
            output = executor._invoke_script(sample_read_script, params)
            assert "Server: web-server-01" in output
        finally:
            if os.path.exists(f.name):
                os.unlink(f.name)
    
    def test_invoke_script_not_found_raises_error(self, executor, sample_read_script):
        """Non-existent script should raise error."""
        sample_read_script.file_path = "/nonexistent/script.py"
        
        with pytest.raises(TaskExecutorError) as exc_info:
            executor._invoke_script(sample_read_script, {})
        assert "not found" in str(exc_info.value).lower() or "failed" in str(exc_info.value).lower()
    
    def test_invoke_script_timeout_raises_error(self, executor, admin_user, sample_read_script):
        """Script timeout should raise error."""
        # Register the script first using executor's registry
        executor.script_registry.register_script(sample_read_script, admin_user)
        
        # Create a script that sleeps longer than timeout (use 0.1 seconds for quick test)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('#!/usr/bin/env python3\nimport time\ntime.sleep(10)\n')
            f.flush()
            sample_read_script.file_path = f.name
        
        try:
            # Temporarily set a very short timeout for this test
            original_timeout = config.SCRIPT_EXECUTION_TIMEOUT
            config.SCRIPT_EXECUTION_TIMEOUT = 1
            
            try:
                with pytest.raises(TaskExecutorError) as exc_info:
                    executor._invoke_script(sample_read_script, {})
                assert "timed out" in str(exc_info.value).lower()
            finally:
                config.SCRIPT_EXECUTION_TIMEOUT = original_timeout
        finally:
            if os.path.exists(f.name):
                os.unlink(f.name)


class TestTaskExecutorIntegration:
    """Integration tests for Task Executor."""
    
    def test_full_read_action_flow(self, executor, admin_user, sample_read_script):
        """Test complete read action flow."""
        # Register the script
        executor.script_registry.register_script(sample_read_script, admin_user)
        
        # Create a task
        task = Task(
            intent=Intent.CHECK_STATUS,
            entities=[Entity(entity_type=EntityType.SERVER, value="web-server-01")],
            script_id="read_script_001",
            parameters={},
            is_write_action=False
        )
        
        # Execute the task
        result = executor.execute_task(task, admin_user)
        assert result is not None
        assert isinstance(result, ExecutionResult)
    
    def test_full_write_action_flow_with_confirmation(self, executor, admin_user, sample_write_script):
        """Test complete write action flow with confirmation."""
        # Register the script
        executor.script_registry.register_script(sample_write_script, admin_user)
        
        # Create a task
        task = Task(
            intent=Intent.RESTART_SERVICE,
            entities=[Entity(entity_type=EntityType.SERVICE, value="nginx")],
            script_id="write_script_001",
            parameters={},
            is_write_action=True
        )
        
        # Execute the task (should create confirmation prompt)
        result = executor.execute_task(task, admin_user)
        assert result is not None
        assert result.success is True
        assert "Confirmation required" in result.output
    
    def test_script_not_found_raises_error(self, admin_user, executor):
        """Execute task with non-existent script should raise error."""
        task = Task(
            intent=Intent.CHECK_STATUS,
            entities=[],
            script_id="nonexistent_script",
            parameters={},
            is_write_action=False
        )
        
        result = executor.execute_task(task, admin_user)
        assert result.success is False
        assert result.error is not None
