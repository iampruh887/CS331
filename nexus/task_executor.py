"""
Task Executor for the Nexus Intelligent Chatbot System.

Orchestrates task execution, handles confirmations for write actions,
masks sensitive data, and coordinates with Script Registry.
"""

import os
import re
import subprocess
import uuid
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import threading

from nexus.database import db, DatabaseError
from nexus.models import (
    Task, ExecutionResult, ConfirmationPrompt, Script, User, UserRole, Intent,
    EntityType, Entity, ScriptLanguage
)
from nexus.script_registry import ScriptRegistry, ScriptRegistryError
from nexus.config import config


class TaskExecutorError(Exception):
    """Raised when task execution fails."""
    pass


class TaskExecutor:
    """
    Orchestrates task execution with confirmation handling and sensitive data masking.
    
    Manages task queue, executes scripts, handles write action confirmations,
    and ensures sensitive data is masked in outputs.
    """
    
    # Sensitive data patterns to mask
    SENSITIVE_PATTERNS = [
        # Password patterns
        (r'(?i)(?:password|passwd|pwd)[\s:=]+[^\s,}]+', '[PASSWORD_MASKED]'),
        # API key patterns - more flexible
        (r'(?i)(?:api[_-]?key|apikey)[\s:=]*[\'"]?([a-zA-Z0-9_\-]{10,})[\'"]?', '[API_KEY_MASKED]'),
        # Token patterns
        (r'(?i)(?:token|bearer)[\s:=]+[^\s,}]+', '[TOKEN_MASKED]'),
        # Secret patterns
        (r'(?i)(?:secret)[\s:=]+[^\s,}]+', '[SECRET_MASKED]'),
        # Private key patterns
        (r'-----BEGIN (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----.*?-----END (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----', '[PRIVATE_KEY_MASKED]'),
        # AWS credentials
        (r'AKIA[0-9A-Z]{16}', '[AWS_ACCESS_KEY_MASKED]'),
        # Generic key patterns
        (r'(?i)(?:key|secret|token)[\s:=]*[\'"]?([a-zA-Z0-9_\-]{20,})[\'"]?', '[KEY_MASKED]'),
        # API key with sk- prefix
        (r'sk-[a-zA-Z0-9_\-]{10,}', '[API_KEY_MASKED]'),
    ]
    
    def __init__(
        self,
        script_registry: ScriptRegistry = None,
        database: db = None,
        max_concurrent_tasks: int = None
    ):
        """
        Initialize Task Executor.
        
        Args:
            script_registry: ScriptRegistry instance. Uses global if not provided.
            database: Database instance. Uses global if not provided.
            max_concurrent_tasks: Maximum concurrent tasks. Uses config if not provided.
        """
        self.script_registry = script_registry or ScriptRegistry()
        self.db = database or db
        self.max_concurrent_tasks = max_concurrent_tasks or config.MAX_CONCURRENT_TASKS
        
        # Task queue management
        self._task_queue: List[str] = []
        self._active_tasks: Dict[str, threading.Event] = {}
        self._active_tasks_lock = threading.Lock()
        
        # Confirmation prompts storage (in-memory + database)
        self._confirmation_prompts: Dict[str, ConfirmationPrompt] = {}
        self._confirmation_prompts_lock = threading.Lock()
        
        # Thread pool for concurrent task execution
        self._executor = ThreadPoolExecutor(max_workers=self.max_concurrent_tasks)
    
    def requires_confirmation(self, task: Task) -> bool:
        """
        Check if task is a write action requiring confirmation.
        
        Args:
            task: Task to check
            
        Returns:
            True if task is a write action, False otherwise
        """
        return task.is_write_action
    
    def execute_task(self, task: Task, user: User) -> ExecutionResult:
        """
        Execute a task with appropriate handling.
        
        For write actions, generates a confirmation prompt.
        For read actions, executes immediately.
        
        Args:
            task: Task containing intent, entities, and script info
            user: Authenticated user
            
        Returns:
            ExecutionResult with success status, output, and execution time
        """
        start_time = time.time()
        
        try:
            # Check if task requires confirmation
            if self.requires_confirmation(task):
                # Generate confirmation prompt
                prompt = self.execute_with_confirmation(task, user)
                return ExecutionResult(
                    success=True,
                    output=f"Confirmation required for: {task.intent.value}",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    timestamp=datetime.utcnow()
                )
            
            # Execute read action immediately
            return self._execute_task_direct(task, user)
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
                timestamp=datetime.utcnow()
            )
    
    def _execute_task_direct(self, task: Task, user: User) -> ExecutionResult:
        """
        Execute task directly without confirmation.
        
        Args:
            task: Task to execute
            user: Authenticated user
            
        Returns:
            ExecutionResult with execution outcome
        """
        start_time = time.time()
        
        try:
            # Get script from registry
            script = self.script_registry.get_script(task.script_id)
            if not script:
                raise TaskExecutorError(f"Script '{task.script_id}' not found")
            
            # Build parameters
            params = self._build_script_parameters(task, script)
            
            # Execute script
            output = self._invoke_script(script, params)
            
            # Mask sensitive data
            masked_output = self._mask_sensitive_data(output)
            
            return ExecutionResult(
                success=True,
                output=masked_output,
                execution_time_ms=int((time.time() - start_time) * 1000),
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
                timestamp=datetime.utcnow()
            )
    
    def execute_with_confirmation(self, task: Task, user: User) -> ConfirmationPrompt:
        """
        Generate confirmation prompt for write actions.
        
        Args:
            task: Task requiring confirmation
            user: Authenticated user
            
        Returns:
            ConfirmationPrompt for user to confirm or cancel
        """
        # Generate unique prompt ID
        prompt_id = str(uuid.uuid4())
        
        # Calculate expiry time
        expiry_time = datetime.utcnow() + timedelta(minutes=config.CONFIRMATION_EXPIRY_MINUTES)
        
        # Create confirmation message
        message = self._build_confirmation_message(task, user)
        
        # Create confirmation prompt
        prompt = ConfirmationPrompt(
            prompt_id=prompt_id,
            message=message,
            task=task,
            user_id=user.user_id,
            expiry_time=expiry_time
        )
        
        # Store in memory
        with self._confirmation_prompts_lock:
            self._confirmation_prompts[prompt_id] = prompt
        
        # Store in database
        task_json = self._serialize_task(task)
        self.db.insert_confirmation_prompt(
            prompt_id=prompt_id,
            message=message,
            task_json=task_json,
            user_id=user.user_id,
            expiry_time=expiry_time
        )
        
        return prompt
    
    def confirm_and_execute(self, prompt_id: str, confirmed: bool, user: User) -> ExecutionResult:
        """
        Execute task after confirmation or abort if canceled.
        
        Args:
            prompt_id: Confirmation prompt ID
            confirmed: Whether user confirmed the action
            user: Authenticated user
            
        Returns:
            ExecutionResult with execution outcome or cancellation message
        """
        # Retrieve confirmation prompt
        with self._confirmation_prompts_lock:
            prompt = self._confirmation_prompts.get(prompt_id)
        
        if not prompt:
            # Try database
            prompt_data = self.db.get_confirmation_prompt(prompt_id)
            if prompt_data:
                task = self._deserialize_task(prompt_data['task_json'])
                prompt = ConfirmationPrompt(
                    prompt_id=prompt_id,
                    message=prompt_data['message'],
                    task=task,
                    user_id=prompt_data['user_id'],
                    expiry_time=datetime.fromisoformat(prompt_data['expiry_time']),
                    confirmed=confirmed
                )
        
        if not prompt:
            raise TaskExecutorError(f"Confirmation prompt '{prompt_id}' not found")
        
        # Check expiry
        if datetime.utcnow() > prompt.expiry_time:
            raise TaskExecutorError("Confirmation prompt has expired")
        
        # Check user authorization
        if prompt.user_id != user.user_id:
            raise TaskExecutorError("User not authorized to confirm this action")
        
        if confirmed:
            # Execute the task
            result = self._execute_task_direct(prompt.task, user)
            
            # Mark as confirmed in database
            self.db.update_confirmation_status(prompt_id, True)
            
            # Remove from memory
            with self._confirmation_prompts_lock:
                self._confirmation_prompts.pop(prompt_id, None)
            
            return result
        else:
            # Cancel the action
            # Mark as canceled in database
            self.db.update_confirmation_status(prompt_id, False)
            
            # Remove from memory
            with self._confirmation_prompts_lock:
                self._confirmation_prompts.pop(prompt_id, None)
            
            return ExecutionResult(
                success=False,
                output="Action canceled by user",
                error="User canceled confirmation",
                execution_time_ms=0,
                timestamp=datetime.utcnow()
            )
    
    def _build_script_parameters(self, task: Task, script: Script) -> Dict[str, Any]:
        """
        Build script parameters from task entities.
        
        Args:
            task: Task with entities
            script: Script definition
            
        Returns:
            Dictionary of parameter names to values
        """
        params = {}
        
        # Map entities to script parameters
        for param in script.parameters:
            # Find matching entity by type
            for entity in task.entities:
                if param.name.lower() in [entity.entity_type.value, entity.entity_type.value.replace('_', '')]:
                    params[param.name] = entity.value
                    break
            
            # If not found by type, try to find by name in entities
            if param.name not in params:
                for entity in task.entities:
                    if param.name.lower() in entity.value.lower():
                        params[param.name] = entity.value
                        break
            
            # Use task parameters if available
            if param.name in task.parameters:
                params[param.name] = task.parameters[param.name]
        
        return params
    
    def _build_confirmation_message(self, task: Task, user: User) -> str:
        """
        Build confirmation message for write action.
        
        Args:
            task: Task requiring confirmation
            user: Authenticated user
            
        Returns:
            Human-readable confirmation message
        """
        intent = task.intent.value.replace('_', ' ').title()
        script = self.script_registry.get_script(task.script_id)
        script_name = script.name if script else task.script_id
        
        return (
            f"⚠️  Write Action Confirmation\n\n"
            f"User: {user.email}\n"
            f"Action: {intent}\n"
            f"Script: {script_name}\n"
            f"Parameters: {task.parameters}\n\n"
            f"Type 'confirm' to execute or 'cancel' to abort."
        )
    
    def _mask_sensitive_data(self, output: str) -> str:
        """
        Mask sensitive data in output.
        
        Scans output for sensitive patterns and replaces with masked placeholders.
        
        Args:
            output: Raw output string
            
        Returns:
            Output with sensitive data masked
        """
        masked_output = output
        
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            masked_output = re.sub(pattern, replacement, masked_output, flags=re.DOTALL)
        
        return masked_output
    
    def _invoke_script(self, script: Script, params: Dict[str, Any]) -> str:
        """
        Execute external script with parameters.
        
        Args:
            script: Script to execute
            params: Script parameters
            
        Returns:
            Script output (stdout)
            
        Raises:
            TaskExecutorError: If script execution fails
        """
        try:
            # Build command
            if script.language == ScriptLanguage.PYTHON:
                cmd = ["python3", script.file_path]
            elif script.language == ScriptLanguage.BASH:
                cmd = ["bash", script.file_path]
            else:
                raise TaskExecutorError(f"Unsupported script language: {script.language}")
            
            # Add parameters
            for param_name, param_value in params.items():
                cmd.extend([f"--{param_name}", str(param_value)])
            
            # Execute script with timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=config.SCRIPT_EXECUTION_TIMEOUT
            )
            
            # Check for errors
            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else result.stdout
                raise TaskExecutorError(f"Script execution failed: {error_msg}")
            
            return result.stdout
            
        except subprocess.TimeoutExpired:
            raise TaskExecutorError(
                f"Script execution timed out after {config.SCRIPT_EXECUTION_TIMEOUT} seconds"
            )
        except FileNotFoundError:
            raise TaskExecutorError(f"Script not found: {script.file_path}")
        except Exception as e:
            raise TaskExecutorError(f"Failed to execute script: {str(e)}") from e
    
    def _serialize_task(self, task: Task) -> str:
        """
        Serialize task to JSON string.
        
        Args:
            task: Task to serialize
            
        Returns:
            JSON string representation
        """
        import json
        
        return json.dumps({
            'intent': task.intent.value,
            'entities': [
                {
                    'entity_type': e.entity_type.value,
                    'value': e.value,
                    'confidence': e.confidence
                } for e in task.entities
            ],
            'script_id': task.script_id,
            'parameters': task.parameters,
            'is_write_action': task.is_write_action
        })
    
    def _deserialize_task(self, task_json: str) -> Task:
        """
        Deserialize task from JSON string.
        
        Args:
            task_json: JSON string representation
            
        Returns:
            Task object
        """
        import json
        
        data = json.loads(task_json)
        
        return Task(
            intent=Intent(data['intent']),
            entities=[
                Entity(
                    entity_type=EntityType(e['entity_type']),
                    value=e['value'],
                    confidence=e.get('confidence', 1.0)
                ) for e in data['entities']
            ],
            script_id=data['script_id'],
            parameters=data['parameters'],
            is_write_action=data['is_write_action']
        )
    
    def cleanup_expired_prompts(self) -> int:
        """
        Remove expired confirmation prompts.
        
        Returns:
            Number of prompts removed
        """
        now = datetime.utcnow()
        removed = 0
        
        with self._confirmation_prompts_lock:
            expired_ids = [
                prompt_id for prompt_id, prompt in self._confirmation_prompts.items()
                if now > prompt.expiry_time
            ]
            
            for prompt_id in expired_ids:
                del self._confirmation_prompts[prompt_id]
                removed += 1
        
        return removed
    
    def shutdown(self):
        """Shutdown the task executor and clean up resources."""
        self._executor.shutdown(wait=True)


# Global task executor instance
task_executor = TaskExecutor()
