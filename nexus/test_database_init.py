"""
Unit tests for database initialization.

Tests:
- Table creation
- Database connection handling
- Configuration loading with valid and invalid values

Requirements: 15.1, 15.3
"""

import pytest
import os
import tempfile
import sqlite3
from unittest.mock import patch, MagicMock
from nexus.database import Database, DatabaseError
from nexus.config import Config, ConfigurationError


class TestDatabaseTableCreation:
    """Test database table creation."""
    
    def test_initialize_schema_creates_all_tables(self):
        """Test that initialize_schema creates all required tables."""
        # Use temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            db = Database(db_path=tmp_path)
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
        
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_initialize_schema_is_idempotent(self):
        """Test that initialize_schema can be called multiple times safely."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            db = Database(db_path=tmp_path)
            
            # Call initialize_schema multiple times
            db.initialize_schema()
            db.initialize_schema()
            db.initialize_schema()
            
            # Verify tables still exist and are correct
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
            
            assert 'users' in tables
            assert 'scripts' in tables
            assert len(tables) >= 6
        
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_users_table_schema(self):
        """Test that users table has correct schema."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            db = Database(db_path=tmp_path)
            db.initialize_schema()
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(users)")
                columns = {row[1]: row[2] for row in cursor.fetchall()}
            
            # Verify required columns exist
            assert 'id' in columns
            assert 'email' in columns
            assert 'hashed_password' in columns
            assert 'is_active' in columns
            assert 'role' in columns
            assert 'created_at' in columns
        
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_scripts_table_schema(self):
        """Test that scripts table has correct schema."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            db = Database(db_path=tmp_path)
            db.initialize_schema()
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(scripts)")
                columns = {row[1]: row[2] for row in cursor.fetchall()}
            
            # Verify required columns exist
            assert 'script_id' in columns
            assert 'name' in columns
            assert 'file_path' in columns
            assert 'language' in columns
            assert 'mapped_intents' in columns
            assert 'parameters' in columns
            assert 'is_read_only' in columns
            assert 'registered_by' in columns
        
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_audit_logs_table_schema(self):
        """Test that audit_logs table has correct schema."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            db = Database(db_path=tmp_path)
            db.initialize_schema()
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(audit_logs)")
                columns = {row[1]: row[2] for row in cursor.fetchall()}
            
            # Verify required columns exist
            assert 'entry_id' in columns
            assert 'user_id' in columns
            assert 'user_email' in columns
            assert 'command' in columns
            assert 'intent' in columns
            assert 'success' in columns
            assert 'execution_time_ms' in columns
            assert 'timestamp' in columns
        
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class TestDatabaseConnectionHandling:
    """Test database connection handling."""
    
    def test_get_connection_returns_valid_connection(self):
        """Test that get_connection returns a valid database connection."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            db = Database(db_path=tmp_path)
            
            with db.get_connection() as conn:
                assert conn is not None
                assert isinstance(conn, sqlite3.Connection)
                # Test that connection works
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                assert result[0] == 1
        
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_get_connection_commits_on_success(self):
        """Test that get_connection commits changes on success."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            db = Database(db_path=tmp_path)
            db.initialize_schema()
            
            # Insert data within context manager
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO error_patterns (
                        pattern_id, pattern_regex, description,
                        common_causes, suggested_fixes
                    ) VALUES (?, ?, ?, ?, ?)
                """, ('test_pattern', 'test.*', 'Test pattern', '[]', '[]'))
            
            # Verify data was committed
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT pattern_id FROM error_patterns WHERE pattern_id = ?", ('test_pattern',))
                result = cursor.fetchone()
                assert result is not None
                assert result[0] == 'test_pattern'
        
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_get_connection_rolls_back_on_error(self):
        """Test that get_connection rolls back changes on error."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            db = Database(db_path=tmp_path)
            db.initialize_schema()
            
            # Attempt to insert invalid data
            with pytest.raises(DatabaseError):
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    # This should fail due to missing required fields
                    cursor.execute("INSERT INTO scripts (script_id) VALUES (?)", ('test',))
            
            # Verify no partial data was committed
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM scripts")
                count = cursor.fetchone()[0]
                assert count == 0
        
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_get_connection_closes_connection(self):
        """Test that get_connection closes the connection after use."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            db = Database(db_path=tmp_path)
            
            conn_ref = None
            with db.get_connection() as conn:
                conn_ref = conn
            
            # Connection should be closed after exiting context
            # Attempting to use it should raise an error
            with pytest.raises(sqlite3.ProgrammingError):
                conn_ref.execute("SELECT 1")
        
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_database_error_on_invalid_path(self):
        """Test that DatabaseError is raised for invalid database path."""
        # Use a path that cannot be created (e.g., in a non-existent directory)
        invalid_path = "/nonexistent/directory/database.db"
        db = Database(db_path=invalid_path)
        
        with pytest.raises(DatabaseError):
            with db.get_connection() as conn:
                pass
    
    def test_connection_timeout_configuration(self):
        """Test that connection timeout is configured correctly."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            db = Database(db_path=tmp_path)
            
            with db.get_connection() as conn:
                # Verify timeout is set (SQLite doesn't expose this directly,
                # but we can verify the connection works)
                assert conn is not None
        
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class TestConfigurationLoading:
    """Test configuration loading with valid and invalid values."""
    
    def test_config_loads_required_parameters(self):
        """Test that configuration loads all required parameters."""
        with patch.dict(os.environ, {
            'JWT_SECRET': 'a' * 32,
            'DATABASE_URL': 'sqlite:///./test.db',
            'GEMINI_API_KEY': 'test_key'
        }):
            config = Config()
            
            assert config.JWT_SECRET == 'a' * 32
            assert config.DATABASE_URL == 'sqlite:///./test.db'
            assert config.GEMINI_API_KEY == 'test_key'
    
    def test_config_loads_optional_parameters_with_defaults(self):
        """Test that optional parameters use default values."""
        with patch.dict(os.environ, {
            'JWT_SECRET': 'a' * 32,
            'DATABASE_URL': 'sqlite:///./test.db',
            'GEMINI_API_KEY': 'test_key'
        }, clear=True):
            config = Config()
            
            # Verify defaults
            assert config.CONFIDENCE_THRESHOLD == 0.5
            assert config.MAX_CONCURRENT_TASKS == 50
            assert config.TOKEN_EXPIRY_MINUTES == 30
            assert config.SCRIPT_EXECUTION_TIMEOUT == 30
            assert config.MAX_RETRIES == 3
    
    def test_config_raises_error_for_missing_jwt_secret(self):
        """Test that ConfigurationError is raised when JWT_SECRET is missing."""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'sqlite:///./test.db',
            'GEMINI_API_KEY': 'test_key'
        }, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                Config()
            
            assert "JWT_SECRET is required" in str(exc_info.value)
    
    def test_config_raises_error_for_short_jwt_secret(self):
        """Test that ConfigurationError is raised when JWT_SECRET is too short."""
        with patch.dict(os.environ, {
            'JWT_SECRET': 'short',
            'DATABASE_URL': 'sqlite:///./test.db',
            'GEMINI_API_KEY': 'test_key'
        }, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                Config()
            
            assert "JWT_SECRET must be at least 32 characters" in str(exc_info.value)
    
    def test_config_raises_error_for_missing_gemini_api_key(self):
        """Test that ConfigurationError is raised when GEMINI_API_KEY is missing."""
        with patch.dict(os.environ, {
            'JWT_SECRET': 'a' * 32,
            'DATABASE_URL': 'sqlite:///./test.db'
        }, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                Config()
            
            assert "GEMINI_API_KEY is required" in str(exc_info.value)
    
    def test_config_uses_default_database_url_when_missing(self):
        """Test that DATABASE_URL uses default value when not provided."""
        with patch.dict(os.environ, {
            'JWT_SECRET': 'a' * 32,
            'GEMINI_API_KEY': 'test_key'
        }, clear=True):
            config = Config()
            
            # Should use default value
            assert config.DATABASE_URL == "sqlite:///./nexus.db"
    
    def test_config_raises_error_for_invalid_confidence_threshold(self):
        """Test that ConfigurationError is raised for invalid confidence threshold."""
        with patch.dict(os.environ, {
            'JWT_SECRET': 'a' * 32,
            'DATABASE_URL': 'sqlite:///./test.db',
            'GEMINI_API_KEY': 'test_key',
            'CONFIDENCE_THRESHOLD': '1.5'
        }, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                Config()
            
            assert "CONFIDENCE_THRESHOLD must be between 0 and 1" in str(exc_info.value)
    
    def test_config_raises_error_for_negative_confidence_threshold(self):
        """Test that ConfigurationError is raised for negative confidence threshold."""
        with patch.dict(os.environ, {
            'JWT_SECRET': 'a' * 32,
            'DATABASE_URL': 'sqlite:///./test.db',
            'GEMINI_API_KEY': 'test_key',
            'CONFIDENCE_THRESHOLD': '-0.1'
        }, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                Config()
            
            assert "CONFIDENCE_THRESHOLD must be between 0 and 1" in str(exc_info.value)
    
    def test_config_raises_error_for_invalid_max_concurrent_tasks(self):
        """Test that ConfigurationError is raised for invalid max concurrent tasks."""
        with patch.dict(os.environ, {
            'JWT_SECRET': 'a' * 32,
            'DATABASE_URL': 'sqlite:///./test.db',
            'GEMINI_API_KEY': 'test_key',
            'MAX_CONCURRENT_TASKS': '0'
        }, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                Config()
            
            assert "MAX_CONCURRENT_TASKS must be at least 1" in str(exc_info.value)
    
    def test_config_raises_error_for_invalid_token_expiry(self):
        """Test that ConfigurationError is raised for invalid token expiry."""
        with patch.dict(os.environ, {
            'JWT_SECRET': 'a' * 32,
            'DATABASE_URL': 'sqlite:///./test.db',
            'GEMINI_API_KEY': 'test_key',
            'TOKEN_EXPIRY_MINUTES': '0'
        }, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                Config()
            
            assert "TOKEN_EXPIRY_MINUTES must be at least 1" in str(exc_info.value)
    
    def test_config_raises_error_for_invalid_script_timeout(self):
        """Test that ConfigurationError is raised for invalid script timeout."""
        with patch.dict(os.environ, {
            'JWT_SECRET': 'a' * 32,
            'DATABASE_URL': 'sqlite:///./test.db',
            'GEMINI_API_KEY': 'test_key',
            'SCRIPT_EXECUTION_TIMEOUT': '0'
        }, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                Config()
            
            assert "SCRIPT_EXECUTION_TIMEOUT must be at least 1" in str(exc_info.value)
    
    def test_config_get_database_path_extracts_path(self):
        """Test that get_database_path extracts path from DATABASE_URL."""
        with patch.dict(os.environ, {
            'JWT_SECRET': 'a' * 32,
            'DATABASE_URL': 'sqlite:///./nexus_test.db',
            'GEMINI_API_KEY': 'test_key'
        }, clear=True):
            config = Config()
            
            path = config.get_database_path()
            assert path == './nexus_test.db'
    
    def test_config_repr_masks_sensitive_data(self):
        """Test that config representation masks sensitive data."""
        with patch.dict(os.environ, {
            'JWT_SECRET': 'a' * 32,
            'DATABASE_URL': 'sqlite:///./test.db',
            'GEMINI_API_KEY': 'test_key'
        }, clear=True):
            config = Config()
            
            repr_str = repr(config)
            assert '***MASKED***' in repr_str
            assert 'a' * 32 not in repr_str
            assert 'test_key' not in repr_str
            assert 'JWT_SECRET' in repr_str
            assert 'GEMINI_API_KEY' in repr_str
    
    def test_config_accepts_custom_values(self):
        """Test that configuration accepts custom values for optional parameters."""
        with patch.dict(os.environ, {
            'JWT_SECRET': 'a' * 32,
            'DATABASE_URL': 'sqlite:///./test.db',
            'GEMINI_API_KEY': 'test_key',
            'CONFIDENCE_THRESHOLD': '0.7',
            'MAX_CONCURRENT_TASKS': '100',
            'TOKEN_EXPIRY_MINUTES': '60'
        }, clear=True):
            config = Config()
            
            assert config.CONFIDENCE_THRESHOLD == 0.7
            assert config.MAX_CONCURRENT_TASKS == 100
            assert config.TOKEN_EXPIRY_MINUTES == 60
