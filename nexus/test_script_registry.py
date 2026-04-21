"""
Unit tests for the Script Registry component.

Tests all CRUD operations and authorization checks.
"""

import pytest
import tempfile
import os
from datetime import datetime
from pathlib import Path

from nexus.script_registry import ScriptRegistry, ScriptRegistryError
from nexus.models import (
    Script, ScriptLanguage, Intent, Parameter, User, UserRole
)
from nexus.database import db as global_db


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
def script_registry(test_db_path):
    """Create a ScriptRegistry instance with test database."""
    from nexus.database import Database
    test_db = Database(test_db_path)
    test_db.initialize_schema()
    return ScriptRegistry(test_db)


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
def sample_script():
    """Create a sample script for testing."""
    return Script(
        script_id="test_script_001",
        name="Test Script",
        file_path="/scripts/test_script.py",
        language=ScriptLanguage.PYTHON,
        mapped_intents=[Intent.CHECK_STATUS, Intent.QUERY_METRICS],
        parameters=[
            Parameter(name="server", type="string", required=True, description="Server name"),
            Parameter(name="port", type="int", required=False, description="Port number")
        ],
        is_read_only=True,
        registered_by="admin@example.com"
    )


class TestScriptRegistryAuthorization:
    """Tests for authorization checks in Script Registry."""
    
    def test_register_script_with_admin_user(self, script_registry, admin_user, sample_script):
        """Admin user should be able to register scripts."""
        result = script_registry.register_script(sample_script, admin_user)
        assert result is True
    
    def test_register_script_with_general_user_raises_error(self, script_registry, general_user, sample_script):
        """General user should not be able to register scripts."""
        with pytest.raises(ScriptRegistryError) as exc_info:
            script_registry.register_script(sample_script, general_user)
        assert "not authorized" in str(exc_info.value)
        assert "ADMIN" in str(exc_info.value)
    
    def test_unregister_script_with_admin_user(self, script_registry, admin_user, sample_script):
        """Admin user should be able to unregister scripts."""
        # First register the script
        script_registry.register_script(sample_script, admin_user)
        
        # Then unregister it
        result = script_registry.unregister_script(sample_script.script_id, admin_user)
        assert result is True
    
    def test_unregister_script_with_general_user_raises_error(self, script_registry, general_user, sample_script):
        """General user should not be able to unregister scripts."""
        with pytest.raises(ScriptRegistryError) as exc_info:
            script_registry.unregister_script(sample_script.script_id, general_user)
        assert "not authorized" in str(exc_info.value)
        assert "ADMIN" in str(exc_info.value)
    
    def test_list_all_scripts_requires_no_auth(self, script_registry, general_user):
        """Listing scripts should not require authorization."""
        # This should not raise any error
        scripts = script_registry.list_all_scripts()
        assert isinstance(scripts, list)


class TestScriptRegistryCRUD:
    """Tests for CRUD operations in Script Registry."""
    
    def test_register_script_success(self, script_registry, admin_user, sample_script):
        """Successfully register a script."""
        result = script_registry.register_script(sample_script, admin_user)
        assert result is True
    
    def test_register_duplicate_script_fails(self, script_registry, admin_user, sample_script):
        """Registering a duplicate script should fail."""
        # Register first time
        script_registry.register_script(sample_script, admin_user)
        
        # Try to register again - should raise ScriptRegistryError
        with pytest.raises(ScriptRegistryError) as exc_info:
            script_registry.register_script(sample_script, admin_user)
        assert "already exist" in str(exc_info.value)
    
    def test_get_script_existing(self, script_registry, admin_user, sample_script):
        """Retrieve an existing script."""
        script_registry.register_script(sample_script, admin_user)
        
        retrieved = script_registry.get_script(sample_script.script_id)
        assert retrieved is not None
        assert retrieved.script_id == sample_script.script_id
        assert retrieved.name == sample_script.name
    
    def test_get_script_nonexistent(self, script_registry):
        """Retrieve a non-existent script returns None."""
        result = script_registry.get_script("nonexistent_script")
        assert result is None
    
    def test_find_scripts_by_intent(self, script_registry, admin_user):
        """Find scripts by intent."""
        script1 = Script(
            script_id="script1",
            name="Script 1",
            file_path="/scripts/script1.py",
            language=ScriptLanguage.PYTHON,
            mapped_intents=[Intent.CHECK_STATUS],
            parameters=[],
            is_read_only=True,
            registered_by="admin@example.com"
        )
        
        script2 = Script(
            script_id="script2",
            name="Script 2",
            file_path="/scripts/script2.py",
            language=ScriptLanguage.BASH,
            mapped_intents=[Intent.CHECK_STATUS, Intent.RESTART_SERVICE],
            parameters=[],
            is_read_only=True,
            registered_by="admin@example.com"
        )
        
        script_registry.register_script(script1, admin_user)
        script_registry.register_script(script2, admin_user)
        
        # Find by CHECK_STATUS
        results = script_registry.find_scripts_by_intent(Intent.CHECK_STATUS)
        assert len(results) == 2
        
        # Find by RESTART_SERVICE
        results = script_registry.find_scripts_by_intent(Intent.RESTART_SERVICE)
        assert len(results) == 1
        assert results[0].script_id == "script2"
    
    def test_list_all_scripts(self, script_registry, admin_user):
        """List all registered scripts."""
        script1 = Script(
            script_id="script1",
            name="Script 1",
            file_path="/scripts/script1.py",
            language=ScriptLanguage.PYTHON,
            mapped_intents=[Intent.CHECK_STATUS],
            parameters=[],
            is_read_only=True,
            registered_by="admin@example.com"
        )
        
        script2 = Script(
            script_id="script2",
            name="Script 2",
            file_path="/scripts/script2.py",
            language=ScriptLanguage.BASH,
            mapped_intents=[Intent.RESTART_SERVICE],
            parameters=[],
            is_read_only=False,
            registered_by="admin@example.com"
        )
        
        script_registry.register_script(script1, admin_user)
        script_registry.register_script(script2, admin_user)
        
        all_scripts = script_registry.list_all_scripts()
        assert len(all_scripts) == 2
    
    def test_unregister_script(self, script_registry, admin_user, sample_script):
        """Unregister a script."""
        script_registry.register_script(sample_script, admin_user)
        
        # Verify it exists
        assert script_registry.get_script(sample_script.script_id) is not None
        
        # Unregister it
        result = script_registry.unregister_script(sample_script.script_id, admin_user)
        assert result is True
        
        # Verify it's gone
        assert script_registry.get_script(sample_script.script_id) is None


class TestScriptRegistryHelperMethods:
    """Tests for helper methods in Script Registry."""
    
    def test_get_scripts_by_language(self, script_registry, admin_user):
        """Get scripts filtered by language."""
        python_script = Script(
            script_id="python_script",
            name="Python Script",
            file_path="/scripts/python_script.py",
            language=ScriptLanguage.PYTHON,
            mapped_intents=[Intent.CHECK_STATUS],
            parameters=[],
            is_read_only=True,
            registered_by="admin@example.com"
        )
        
        bash_script = Script(
            script_id="bash_script",
            name="Bash Script",
            file_path="/scripts/bash_script.sh",
            language=ScriptLanguage.BASH,
            mapped_intents=[Intent.RESTART_SERVICE],
            parameters=[],
            is_read_only=True,
            registered_by="admin@example.com"
        )
        
        script_registry.register_script(python_script, admin_user)
        script_registry.register_script(bash_script, admin_user)
        
        # Get Python scripts
        python_scripts = script_registry.get_scripts_by_language(ScriptLanguage.PYTHON)
        assert len(python_scripts) == 1
        assert python_scripts[0].script_id == "python_script"
        
        # Get Bash scripts
        bash_scripts = script_registry.get_scripts_by_language(ScriptLanguage.BASH)
        assert len(bash_scripts) == 1
        assert bash_scripts[0].script_id == "bash_script"
    
    def test_get_read_only_scripts(self, script_registry, admin_user):
        """Get only read-only scripts."""
        read_only_script = Script(
            script_id="read_only",
            name="Read Only",
            file_path="/scripts/read_only.py",
            language=ScriptLanguage.PYTHON,
            mapped_intents=[Intent.CHECK_STATUS],
            parameters=[],
            is_read_only=True,
            registered_by="admin@example.com"
        )
        
        write_script = Script(
            script_id="write_script",
            name="Write Script",
            file_path="/scripts/write_script.py",
            language=ScriptLanguage.PYTHON,
            mapped_intents=[Intent.RESTART_SERVICE],
            parameters=[],
            is_read_only=False,
            registered_by="admin@example.com"
        )
        
        script_registry.register_script(read_only_script, admin_user)
        script_registry.register_script(write_script, admin_user)
        
        read_only = script_registry.get_read_only_scripts()
        assert len(read_only) == 1
        assert read_only[0].script_id == "read_only"
    
    def test_get_write_scripts(self, script_registry, admin_user):
        """Get only write-action scripts."""
        read_only_script = Script(
            script_id="read_only",
            name="Read Only",
            file_path="/scripts/read_only.py",
            language=ScriptLanguage.PYTHON,
            mapped_intents=[Intent.CHECK_STATUS],
            parameters=[],
            is_read_only=True,
            registered_by="admin@example.com"
        )
        
        write_script = Script(
            script_id="write_script",
            name="Write Script",
            file_path="/scripts/write_script.py",
            language=ScriptLanguage.PYTHON,
            mapped_intents=[Intent.RESTART_SERVICE],
            parameters=[],
            is_read_only=False,
            registered_by="admin@example.com"
        )
        
        script_registry.register_script(read_only_script, admin_user)
        script_registry.register_script(write_script, admin_user)
        
        write_scripts = script_registry.get_write_scripts()
        assert len(write_scripts) == 1
        assert write_scripts[0].script_id == "write_script"


class TestScriptRegistryIntegration:
    """Integration tests for Script Registry."""
    
    def test_full_registration_workflow(self, script_registry, admin_user):
        """Test complete registration workflow."""
        # Create script
        script = Script(
            script_id="full_test_script",
            name="Full Test Script",
            file_path="/scripts/full_test.py",
            language=ScriptLanguage.PYTHON,
            mapped_intents=[Intent.CHECK_STATUS, Intent.QUERY_METRICS],
            parameters=[
                Parameter(name="server", type="string", required=True, description="Server name"),
                Parameter(name="port", type="int", required=False, description="Port"),
                Parameter(name="timeout", type="int", required=False, description="Timeout in seconds")
            ],
            is_read_only=True,
            registered_by="admin@example.com"
        )
        
        # Register
        result = script_registry.register_script(script, admin_user)
        assert result is True
        
        # Retrieve
        retrieved = script_registry.get_script(script.script_id)
        assert retrieved is not None
        assert len(retrieved.parameters) == 3
        
        # Find by intent
        scripts = script_registry.find_scripts_by_intent(Intent.CHECK_STATUS)
        assert len(scripts) == 1
        
        # List all
        all_scripts = script_registry.list_all_scripts()
        assert len(all_scripts) == 1
    
    def test_script_metadata_preservation(self, script_registry, admin_user):
        """Test that all script metadata is preserved."""
        script = Script(
            script_id="metadata_test",
            name="Metadata Test Script",
            file_path="/scripts/metadata_test.py",
            language=ScriptLanguage.PYTHON,
            mapped_intents=[Intent.CHECK_STATUS],
            parameters=[Parameter(name="test", type="string", required=True, description="Test param")],
            is_read_only=True,
            registered_by="admin@example.com"
        )
        
        script_registry.register_script(script, admin_user)
        retrieved = script_registry.get_script(script.script_id)
        
        assert retrieved.script_id == script.script_id
        assert retrieved.name == script.name
        assert retrieved.file_path == script.file_path
        assert retrieved.language == script.language
        assert retrieved.mapped_intents == script.mapped_intents
        assert retrieved.parameters == script.parameters
        assert retrieved.is_read_only == script.is_read_only
        assert retrieved.registered_by == script.registered_by
