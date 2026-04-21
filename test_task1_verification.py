#!/usr/bin/env python3
"""
Verification script for Task 1: Set up project structure and database schema

This script tests:
1. Configuration management (nexus/config.py)
2. Database initialization (nexus/init_db.py)
3. Data models (nexus/models.py)
4. Database operations (nexus/database.py)
"""

import sys
sys.path.insert(0, '.')

from datetime import datetime, timedelta
from nexus.config import config, ConfigurationError
from nexus.database import db, DatabaseError
from nexus.models import (
    Intent, EntityType, ScriptLanguage, UserRole,
    Entity, ParsedIntent, Message, MessageHistory,
    Parameter, Script, Task, ExecutionResult, ConfirmationPrompt,
    AuditEntry, LogFilter, ExecutionError, ErrorPattern, ErrorAnalysis,
    TimeSlot, AvailabilityRequest, AvailabilityResult,
    MeetingRequest, MeetingResult, Reminder, User
)


def test_configuration():
    """Test configuration management."""
    print("Testing Configuration Management...")
    
    # Test configuration loading
    assert config.JWT_SECRET, "JWT_SECRET should be loaded"
    assert config.DATABASE_URL, "DATABASE_URL should be loaded"
    assert config.GEMINI_API_KEY, "GEMINI_API_KEY should be loaded"
    
    # Test default values
    assert config.CONFIDENCE_THRESHOLD == 0.5, "Default confidence threshold"
    assert config.MAX_CONCURRENT_TASKS == 50, "Default max concurrent tasks"
    assert config.TOKEN_EXPIRY_MINUTES == 30, "Default token expiry"
    
    # Test configuration representation (should mask sensitive data)
    repr_str = repr(config)
    assert "***MASKED***" in repr_str, "Sensitive data should be masked"
    assert "JWT_SECRET" in repr_str, "Should show parameter names"
    
    print("  ✓ Configuration management works correctly")


def test_data_models():
    """Test all data models."""
    print("\nTesting Data Models...")
    
    # Test Entity
    entity = Entity(entity_type=EntityType.SERVER, value='web-01', confidence=0.95)
    assert entity.entity_type == EntityType.SERVER
    assert entity.value == 'web-01'
    
    # Test ParsedIntent
    parsed = ParsedIntent(
        intent=Intent.CHECK_STATUS,
        entities=[entity],
        confidence=0.92,
        raw_command='check status'
    )
    assert parsed.intent == Intent.CHECK_STATUS
    assert len(parsed.entities) == 1
    
    # Test MessageHistory
    history = MessageHistory(user_id='user1')
    for i in range(5):
        msg = Message(
            text=f'message {i}',
            intent=Intent.CHECK_STATUS,
            entities=[],
            timestamp=datetime.utcnow()
        )
        history.add_message(msg)
    assert len(history.messages) == 3, "Should maintain max 3 messages"
    
    # Test Script
    script = Script(
        script_id='test_script',
        name='Test Script',
        file_path='/scripts/test.py',
        language=ScriptLanguage.PYTHON,
        mapped_intents=[Intent.QUERY_METRICS],
        parameters=[Parameter(name='p1', type='string', required=True, description='Param 1')],
        is_read_only=True,
        registered_by='admin@test.com'
    )
    assert script.language == ScriptLanguage.PYTHON
    assert script.is_read_only == True
    
    # Test Task
    task = Task(
        intent=Intent.QUERY_METRICS,
        entities=[entity],
        script_id='test_script',
        parameters={'server': 'web-01'},
        is_write_action=False
    )
    assert task.is_write_action == False
    
    # Test ExecutionResult
    result = ExecutionResult(
        success=True,
        output='CPU: 45%',
        execution_time_ms=150
    )
    assert result.success == True
    
    print("  ✓ All data models work correctly")


def test_database_schema():
    """Test database schema initialization."""
    print("\nTesting Database Schema...")
    
    # Initialize schema (idempotent)
    db.initialize_schema()
    
    # Verify all tables exist
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
    
    required_tables = [
        'users', 'scripts', 'audit_logs', 'error_logs',
        'error_patterns', 'confirmation_prompts'
    ]
    
    for table in required_tables:
        assert table in tables, f"Table {table} should exist"
    
    print("  ✓ Database schema initialized correctly")


def test_script_operations():
    """Test script registry operations."""
    print("\nTesting Script Registry Operations...")
    
    # Clean up test data
    db.delete_script('test_script_ops')
    
    # Test script insertion
    script = Script(
        script_id='test_script_ops',
        name='Test Script Ops',
        file_path='/scripts/test_ops.py',
        language=ScriptLanguage.BASH,
        mapped_intents=[Intent.CHECK_STATUS, Intent.QUERY_METRICS],
        parameters=[
            Parameter(name='server', type='string', required=True, description='Server name'),
            Parameter(name='verbose', type='bool', required=False, description='Verbose output')
        ],
        is_read_only=True,
        registered_by='admin@test.com'
    )
    
    success = db.insert_script(script)
    assert success == True, "Script insertion should succeed"
    
    # Test duplicate insertion
    duplicate = db.insert_script(script)
    assert duplicate == False, "Duplicate insertion should fail"
    
    # Test script retrieval
    retrieved = db.get_script('test_script_ops')
    assert retrieved is not None, "Script should be retrievable"
    assert retrieved.name == 'Test Script Ops'
    assert retrieved.language == ScriptLanguage.BASH
    assert len(retrieved.parameters) == 2
    
    # Test finding by intent
    scripts = db.find_scripts_by_intent(Intent.CHECK_STATUS)
    assert any(s.script_id == 'test_script_ops' for s in scripts), "Should find script by intent"
    
    # Test deletion
    deleted = db.delete_script('test_script_ops')
    assert deleted == True, "Script deletion should succeed"
    
    # Verify deletion
    retrieved_after = db.get_script('test_script_ops')
    assert retrieved_after is None, "Script should be deleted"
    
    print("  ✓ Script registry operations work correctly")


def test_audit_log_operations():
    """Test audit log operations."""
    print("\nTesting Audit Log Operations...")
    
    # Create test audit entry
    result = ExecutionResult(
        success=True,
        output='Test output',
        execution_time_ms=100
    )
    
    entry = AuditEntry(
        entry_id='test_audit_1',
        user_id='user123',
        user_email='user@test.com',
        command='test command',
        intent=Intent.CHECK_STATUS,
        result=result,
        timestamp=datetime.utcnow(),
        execution_time_ms=100
    )
    
    # Insert audit entry
    success = db.insert_audit_entry(entry)
    assert success == True, "Audit entry insertion should succeed"
    
    # Query audit logs
    logs = db.query_audit_logs(user_id='user123')
    assert len(logs) > 0, "Should retrieve audit logs"
    assert logs[0]['user_email'] == 'user@test.com'
    
    # Query with filters
    logs_filtered = db.query_audit_logs(
        intent=Intent.CHECK_STATUS,
        success_only=True
    )
    assert len(logs_filtered) > 0, "Should filter audit logs"
    
    print("  ✓ Audit log operations work correctly")


def test_error_patterns():
    """Test error pattern operations."""
    print("\nTesting Error Pattern Operations...")
    
    # Get all error patterns (should be seeded)
    patterns = db.get_all_error_patterns()
    assert len(patterns) >= 8, "Should have at least 8 seeded patterns"
    
    # Verify pattern structure
    pattern = patterns[0]
    assert pattern.pattern_id, "Pattern should have ID"
    assert pattern.pattern_regex, "Pattern should have regex"
    assert pattern.description, "Pattern should have description"
    assert len(pattern.common_causes) > 0, "Pattern should have common causes"
    assert len(pattern.suggested_fixes) > 0, "Pattern should have suggested fixes"
    
    # Verify specific patterns exist
    pattern_ids = [p.pattern_id for p in patterns]
    expected_patterns = [
        'connection_refused', 'permission_denied', 'file_not_found',
        'timeout', 'authentication_failed'
    ]
    for expected in expected_patterns:
        assert expected in pattern_ids, f"Should have {expected} pattern"
    
    print("  ✓ Error pattern operations work correctly")


def test_confirmation_prompts():
    """Test confirmation prompt operations."""
    print("\nTesting Confirmation Prompt Operations...")
    
    # Insert confirmation prompt
    expiry = datetime.utcnow() + timedelta(minutes=5)
    success = db.insert_confirmation_prompt(
        prompt_id='test_prompt_1',
        message='Confirm restart?',
        task_json='{"intent": "restart_service"}',
        user_id='user123',
        expiry_time=expiry
    )
    assert success == True, "Confirmation prompt insertion should succeed"
    
    # Retrieve confirmation prompt
    prompt = db.get_confirmation_prompt('test_prompt_1')
    assert prompt is not None, "Should retrieve confirmation prompt"
    assert prompt['message'] == 'Confirm restart?'
    assert prompt['confirmed'] is None, "Should be unconfirmed initially"
    
    # Update confirmation status
    updated = db.update_confirmation_status('test_prompt_1', True)
    assert updated == True, "Should update confirmation status"
    
    # Verify update
    prompt_after = db.get_confirmation_prompt('test_prompt_1')
    assert prompt_after['confirmed'] == 1, "Should be confirmed"  # SQLite returns 1 for True
    
    print("  ✓ Confirmation prompt operations work correctly")


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("Task 1 Verification: Project Structure and Database Schema")
    print("=" * 60)
    
    try:
        test_configuration()
        test_data_models()
        test_database_schema()
        test_script_operations()
        test_audit_log_operations()
        test_error_patterns()
        test_confirmation_prompts()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED - Task 1 Complete!")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
