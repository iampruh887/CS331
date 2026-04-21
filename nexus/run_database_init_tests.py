#!/usr/bin/env python3
"""
Simple test runner for database initialization tests.
Runs tests without requiring pytest installation.
"""

import sys
import os
import tempfile
import sqlite3
from unittest.mock import patch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nexus.database import Database, DatabaseError
from nexus.config import Config, ConfigurationError


def test_initialize_schema_creates_all_tables():
    """Test that initialize_schema creates all required tables."""
    print("Testing: initialize_schema creates all tables...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        db = Database(db_path=tmp_path)
        db.initialize_schema()
        
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
        
        print("  ✓ PASSED")
        return True
    
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_initialize_schema_is_idempotent():
    """Test that initialize_schema can be called multiple times safely."""
    print("Testing: initialize_schema is idempotent...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        db = Database(db_path=tmp_path)
        
        db.initialize_schema()
        db.initialize_schema()
        db.initialize_schema()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
        
        assert 'users' in tables
        assert 'scripts' in tables
        assert len(tables) >= 6
        
        print("  ✓ PASSED")
        return True
    
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_users_table_schema():
    """Test that users table has correct schema."""
    print("Testing: users table schema...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        db = Database(db_path=tmp_path)
        db.initialize_schema()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(users)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        assert 'id' in columns
        assert 'email' in columns
        assert 'hashed_password' in columns
        assert 'is_active' in columns
        assert 'role' in columns
        assert 'created_at' in columns
        
        print("  ✓ PASSED")
        return True
    
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_get_connection_returns_valid_connection():
    """Test that get_connection returns a valid database connection."""
    print("Testing: get_connection returns valid connection...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        db = Database(db_path=tmp_path)
        
        with db.get_connection() as conn:
            assert conn is not None
            assert isinstance(conn, sqlite3.Connection)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1
        
        print("  ✓ PASSED")
        return True
    
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_get_connection_commits_on_success():
    """Test that get_connection commits changes on success."""
    print("Testing: get_connection commits on success...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        db = Database(db_path=tmp_path)
        db.initialize_schema()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO error_patterns (
                    pattern_id, pattern_regex, description,
                    common_causes, suggested_fixes
                ) VALUES (?, ?, ?, ?, ?)
            """, ('test_pattern', 'test.*', 'Test pattern', '[]', '[]'))
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT pattern_id FROM error_patterns WHERE pattern_id = ?", ('test_pattern',))
            result = cursor.fetchone()
            assert result is not None
            assert result[0] == 'test_pattern'
        
        print("  ✓ PASSED")
        return True
    
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_get_connection_rolls_back_on_error():
    """Test that get_connection rolls back changes on error."""
    print("Testing: get_connection rolls back on error...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        db = Database(db_path=tmp_path)
        db.initialize_schema()
        
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO scripts (script_id) VALUES (?)", ('test',))
        except DatabaseError:
            pass  # Expected
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM scripts")
            count = cursor.fetchone()[0]
            assert count == 0
        
        print("  ✓ PASSED")
        return True
    
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_config_loads_required_parameters():
    """Test that configuration loads all required parameters."""
    print("Testing: config loads required parameters...")
    
    with patch.dict(os.environ, {
        'JWT_SECRET': 'a' * 32,
        'DATABASE_URL': 'sqlite:///./test.db',
        'GEMINI_API_KEY': 'test_key'
    }):
        config = Config()
        
        assert config.JWT_SECRET == 'a' * 32
        assert config.DATABASE_URL == 'sqlite:///./test.db'
        assert config.GEMINI_API_KEY == 'test_key'
    
    print("  ✓ PASSED")
    return True


def test_config_loads_optional_parameters_with_defaults():
    """Test that optional parameters use default values."""
    print("Testing: config loads optional parameters with defaults...")
    
    with patch.dict(os.environ, {
        'JWT_SECRET': 'a' * 32,
        'DATABASE_URL': 'sqlite:///./test.db',
        'GEMINI_API_KEY': 'test_key'
    }, clear=True):
        config = Config()
        
        assert config.CONFIDENCE_THRESHOLD == 0.5
        assert config.MAX_CONCURRENT_TASKS == 50
        assert config.TOKEN_EXPIRY_MINUTES == 30
        assert config.SCRIPT_EXECUTION_TIMEOUT == 30
        assert config.MAX_RETRIES == 3
    
    print("  ✓ PASSED")
    return True


def test_config_raises_error_for_missing_jwt_secret():
    """Test that ConfigurationError is raised when JWT_SECRET is missing."""
    print("Testing: config raises error for missing JWT_SECRET...")
    
    with patch.dict(os.environ, {
        'DATABASE_URL': 'sqlite:///./test.db',
        'GEMINI_API_KEY': 'test_key'
    }, clear=True):
        try:
            Config()
            assert False, "Should have raised ConfigurationError"
        except ConfigurationError as e:
            assert "JWT_SECRET is required" in str(e)
    
    print("  ✓ PASSED")
    return True


def test_config_raises_error_for_short_jwt_secret():
    """Test that ConfigurationError is raised when JWT_SECRET is too short."""
    print("Testing: config raises error for short JWT_SECRET...")
    
    with patch.dict(os.environ, {
        'JWT_SECRET': 'short',
        'DATABASE_URL': 'sqlite:///./test.db',
        'GEMINI_API_KEY': 'test_key'
    }, clear=True):
        try:
            Config()
            assert False, "Should have raised ConfigurationError"
        except ConfigurationError as e:
            assert "JWT_SECRET must be at least 32 characters" in str(e)
    
    print("  ✓ PASSED")
    return True


def test_config_raises_error_for_invalid_confidence_threshold():
    """Test that ConfigurationError is raised for invalid confidence threshold."""
    print("Testing: config raises error for invalid confidence threshold...")
    
    with patch.dict(os.environ, {
        'JWT_SECRET': 'a' * 32,
        'DATABASE_URL': 'sqlite:///./test.db',
        'GEMINI_API_KEY': 'test_key',
        'CONFIDENCE_THRESHOLD': '1.5'
    }, clear=True):
        try:
            Config()
            assert False, "Should have raised ConfigurationError"
        except ConfigurationError as e:
            assert "CONFIDENCE_THRESHOLD must be between 0 and 1" in str(e)
    
    print("  ✓ PASSED")
    return True


def test_config_get_database_path_extracts_path():
    """Test that get_database_path extracts path from DATABASE_URL."""
    print("Testing: config get_database_path extracts path...")
    
    with patch.dict(os.environ, {
        'JWT_SECRET': 'a' * 32,
        'DATABASE_URL': 'sqlite:///./nexus_test.db',
        'GEMINI_API_KEY': 'test_key'
    }, clear=True):
        config = Config()
        
        path = config.get_database_path()
        assert path == './nexus_test.db'
    
    print("  ✓ PASSED")
    return True


def test_config_repr_masks_sensitive_data():
    """Test that config representation masks sensitive data."""
    print("Testing: config repr masks sensitive data...")
    
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
    
    print("  ✓ PASSED")
    return True


def main():
    """Run all tests."""
    print("=" * 70)
    print("Database Initialization Unit Tests")
    print("=" * 70)
    print()
    
    tests = [
        # Table creation tests
        test_initialize_schema_creates_all_tables,
        test_initialize_schema_is_idempotent,
        test_users_table_schema,
        
        # Connection handling tests
        test_get_connection_returns_valid_connection,
        test_get_connection_commits_on_success,
        test_get_connection_rolls_back_on_error,
        
        # Configuration tests
        test_config_loads_required_parameters,
        test_config_loads_optional_parameters_with_defaults,
        test_config_raises_error_for_missing_jwt_secret,
        test_config_raises_error_for_short_jwt_secret,
        test_config_raises_error_for_invalid_confidence_threshold,
        test_config_get_database_path_extracts_path,
        test_config_repr_masks_sensitive_data,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except AssertionError as e:
            print(f"  ✗ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            failed += 1
    
    print()
    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
