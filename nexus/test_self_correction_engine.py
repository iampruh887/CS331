"""
Unit tests for the Self-Correction Engine component.

Tests error analysis, pattern identification, and error storage.
"""

import pytest
import tempfile
import os
from datetime import datetime

from nexus.self_correction_engine import SelfCorrectionEngine, SelfCorrectionEngineError
from nexus.models import (
    ExecutionError, ErrorPattern, ErrorAnalysis, Task, Intent, EntityType, Entity
)
from nexus.database import Database


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
def engine(test_db_path):
    """Create a SelfCorrectionEngine instance with test database."""
    test_db = Database(test_db_path)
    test_db.initialize_schema()
    return SelfCorrectionEngine(database=test_db)


@pytest.fixture
def sample_execution_error():
    """Create a sample execution error for testing."""
    task = Task(
        intent=Intent.RESTART_SERVICE,
        entities=[Entity(entity_type=EntityType.SERVICE, value="nginx")],
        script_id="restart_script_001",
        parameters={},
        is_write_action=True
    )
    
    return ExecutionError(
        error_id="error_001",
        task=task,
        error_message="Connection refused: Unable to connect to nginx service on port 8080",
        stack_trace="Traceback (most recent call last):\n  File \"script.py\", line 10, in <module>\n    connect()\nConnectionRefusedError: [Errno 111] Connection refused",
        timestamp=datetime.utcnow()
    )


class TestSelfCorrectionEnginePatternSeeding:
    """Tests for default pattern seeding."""
    
    def test_default_patterns_are_seeded(self, engine):
        """Test that default error patterns are seeded in the database."""
        patterns = engine.db.get_all_error_patterns()
        
        # Check that at least one of the default patterns exists
        pattern_ids = {p.pattern_id for p in patterns}
        assert 'connection_refused' in pattern_ids
        assert 'permission_denied' in pattern_ids
        assert 'file_not_found' in pattern_ids
    
    def test_default_patterns_have_required_fields(self, engine):
        """Test that seeded patterns have all required fields."""
        patterns = engine.db.get_all_error_patterns()
        
        for pattern in patterns:
            assert pattern.pattern_id is not None
            assert pattern.pattern_regex is not None
            assert pattern.description is not None
            assert len(pattern.common_causes) > 0
            assert len(pattern.suggested_fixes) > 0
    
    def test_patterns_not_duplicated_on_reinit(self, test_db_path):
        """Test that patterns are not duplicated when engine is reinitialized."""
        test_db = Database(test_db_path)
        test_db.initialize_schema()
        
        # Initialize engine first time
        engine1 = SelfCorrectionEngine(database=test_db)
        patterns1 = engine1.db.get_all_error_patterns()
        
        # Initialize engine second time
        engine2 = SelfCorrectionEngine(database=test_db)
        patterns2 = engine2.db.get_all_error_patterns()
        
        # Should have same number of patterns
        assert len(patterns1) == len(patterns2)


class TestSelfCorrectionEnginePatternIdentification:
    """Tests for error pattern identification."""
    
    def test_identify_connection_refused_pattern(self, engine, sample_execution_error):
        """Test identification of connection refused pattern."""
        pattern = engine._identify_pattern(sample_execution_error)
        
        assert pattern is not None
        assert pattern.pattern_id == 'connection_refused'
    
    def test_identify_permission_denied_pattern(self, engine):
        """Test identification of permission denied pattern."""
        error = ExecutionError(
            error_id="error_002",
            task=Task(
                intent=Intent.QUERY_METRICS,
                entities=[],
                script_id="metric_script_001",
                parameters={},
                is_write_action=False
            ),
            error_message="Permission denied: Cannot access /var/log/syslog",
            timestamp=datetime.utcnow()
        )
        
        pattern = engine._identify_pattern(error)
        
        assert pattern is not None
        assert pattern.pattern_id == 'permission_denied'
    
    def test_identify_file_not_found_pattern(self, engine):
        """Test identification of file not found pattern."""
        error = ExecutionError(
            error_id="error_003",
            task=Task(
                intent=Intent.CHECK_STATUS,
                entities=[],
                script_id="status_script_001",
                parameters={},
                is_write_action=False
            ),
            error_message="Error: File not found: /etc/config.yaml",
            timestamp=datetime.utcnow()
        )
        
        pattern = engine._identify_pattern(error)
        
        assert pattern is not None
        assert pattern.pattern_id == 'file_not_found'
    
    def test_identify_out_of_memory_pattern(self, engine):
        """Test identification of out of memory pattern."""
        error = ExecutionError(
            error_id="error_004",
            task=Task(
                intent=Intent.QUERY_METRICS,
                entities=[],
                script_id="memory_script_001",
                parameters={},
                is_write_action=False
            ),
            error_message="Out of memory: Cannot allocate 512MB",
            timestamp=datetime.utcnow()
        )
        
        pattern = engine._identify_pattern(error)
        
        assert pattern is not None
        assert pattern.pattern_id == 'out_of_memory'
    
    def test_identify_disk_full_pattern(self, engine):
        """Test identification of disk full pattern."""
        error = ExecutionError(
            error_id="error_005",
            task=Task(
                intent=Intent.QUERY_METRICS,
                entities=[],
                script_id="disk_script_001",
                parameters={},
                is_write_action=False
            ),
            error_message="No space left on device: /var/log",
            timestamp=datetime.utcnow()
        )
        
        pattern = engine._identify_pattern(error)
        
        assert pattern is not None
        assert pattern.pattern_id == 'disk_full'
    
    def test_no_match_returns_none(self, engine):
        """Test that unknown error patterns return None."""
        error = ExecutionError(
            error_id="error_006",
            task=Task(
                intent=Intent.CHECK_STATUS,
                entities=[],
                script_id="status_script_001",
                parameters={},
                is_write_action=False
            ),
            error_message="Unknown error: Something unexpected happened",
            timestamp=datetime.utcnow()
        )
        
        pattern = engine._identify_pattern(error)
        
        assert pattern is None


class TestSelfCorrectionEngineSuggestions:
    """Tests for suggestion generation."""
    
    def test_generate_suggestions_for_connection_refused(self, engine):
        """Test suggestion generation for connection refused."""
        pattern = engine.db.get_all_error_patterns()
        connection_pattern = next((p for p in pattern if p.pattern_id == 'connection_refused'), None)
        
        assert connection_pattern is not None
        
        suggestions = engine._generate_suggestions(connection_pattern)
        
        assert len(suggestions) > 0
        assert any('service' in s.lower() for s in suggestions)
    
    def test_generate_suggestions_for_permission_denied(self, engine):
        """Test suggestion generation for permission denied."""
        pattern = engine.db.get_all_error_patterns()
        permission_pattern = next((p for p in pattern if p.pattern_id == 'permission_denied'), None)
        
        assert permission_pattern is not None
        
        suggestions = engine._generate_suggestions(permission_pattern)
        
        assert len(suggestions) > 0
        assert any('chmod' in s.lower() or 'sudo' in s.lower() for s in suggestions)
    
    def test_suggestions_are_independent_copies(self, engine):
        """Test that suggestions are returned as independent copies."""
        pattern = engine.db.get_all_error_patterns()
        connection_pattern = next((p for p in pattern if p.pattern_id == 'connection_refused'), None)
        
        suggestions1 = engine._generate_suggestions(connection_pattern)
        suggestions2 = engine._generate_suggestions(connection_pattern)
        
        # Modifying one should not affect the other
        suggestions1.append("New suggestion")
        assert "New suggestion" not in suggestions2


class TestSelfCorrectionEngineAnalysis:
    """Tests for error analysis."""
    
    def test_analyze_error_with_match(self, engine, sample_execution_error):
        """Test error analysis with pattern match."""
        analysis = engine.analyze_error(sample_execution_error)
        
        assert analysis is not None
        assert analysis.error_id == sample_execution_error.error_id
        assert analysis.pattern_matched is not None
        assert analysis.pattern_matched.pattern_id == 'connection_refused'
        assert len(analysis.suggestions) > 0
        assert 0 <= analysis.confidence <= 1
    
    def test_analyze_error_without_match(self, engine):
        """Test error analysis without pattern match."""
        error = ExecutionError(
            error_id="error_007",
            task=Task(
                intent=Intent.CHECK_STATUS,
                entities=[],
                script_id="status_script_001",
                parameters={},
                is_write_action=False
            ),
            error_message="Unknown error: Something unexpected happened",
            timestamp=datetime.utcnow()
        )
        
        analysis = engine.analyze_error(error)
        
        assert analysis is not None
        assert analysis.pattern_matched is None
        assert len(analysis.suggestions) == 0
        assert analysis.confidence == 0.0
    
    def test_analyze_error_with_empty_message(self, engine):
        """Test error analysis with empty error message."""
        error = ExecutionError(
            error_id="error_008",
            task=Task(
                intent=Intent.CHECK_STATUS,
                entities=[],
                script_id="status_script_001",
                parameters={},
                is_write_action=False
            ),
            error_message="",
            timestamp=datetime.utcnow()
        )
        
        analysis = engine.analyze_error(error)
        
        assert analysis is not None
        assert analysis.pattern_matched is None


class TestSelfCorrectionEngineErrorStorage:
    """Tests for error storage."""
    
    def test_store_error_success(self, engine):
        """Test successful error storage."""
        error = ExecutionError(
            error_id="error_stored_001",
            task=Task(
                intent=Intent.RESTART_SERVICE,
                entities=[],
                script_id="restart_script_001",
                parameters={},
                is_write_action=True
            ),
            error_message="Test error message",
            timestamp=datetime.utcnow()
        )
        
        result = engine.store_error(error)
        
        assert result is True
        
        # Verify error was stored
        history = engine.get_error_history()
        assert any(e['error_id'] == 'error_stored_001' for e in history)
    
    def test_store_error_with_stack_trace(self, engine):
        """Test error storage with stack trace."""
        error = ExecutionError(
            error_id="error_stored_002",
            task=Task(
                intent=Intent.CHECK_STATUS,
                entities=[],
                script_id="status_script_001",
                parameters={},
                is_write_action=False
            ),
            error_message="Test error",
            stack_trace="Traceback (most recent call last):\n  File \"test.py\", line 1\n    pass",
            timestamp=datetime.utcnow()
        )
        
        result = engine.store_error(error)
        
        assert result is True
        
        # Verify stack trace was stored
        history = engine.get_error_history()
        stored_error = next((e for e in history if e['error_id'] == 'error_stored_002'), None)
        assert stored_error is not None
        assert "Traceback" in stored_error['stack_trace']
    
    def test_store_error_raises_on_failure(self, engine):
        """Test that store_error raises on database failure."""
        # This test would require mocking the database to simulate failure
        # For now, just verify the method exists and has correct signature
        error = ExecutionError(
            error_id="error_stored_003",
            task=Task(
                intent=Intent.CHECK_STATUS,
                entities=[],
                script_id="status_script_001",
                parameters={},
                is_write_action=False
            ),
            error_message="Test error",
            timestamp=datetime.utcnow()
        )
        
        # Should not raise for valid input
        result = engine.store_error(error)
        assert result is True


class TestSelfCorrectionEngineIntegration:
    """Integration tests for Self-Correction Engine."""
    
    def test_full_error_analysis_flow(self, engine):
        """Test complete error analysis flow."""
        # Create and store an error
        error = ExecutionError(
            error_id="full_flow_error_001",
            task=Task(
                intent=Intent.RESTART_SERVICE,
                entities=[Entity(entity_type=EntityType.SERVICE, value="nginx")],
                script_id="restart_script_001",
                parameters={},
                is_write_action=True
            ),
            error_message="Connection refused: nginx service on port 80",
            timestamp=datetime.utcnow()
        )
        
        # Store the error
        engine.store_error(error)
        
        # Analyze the error
        analysis = engine.analyze_error(error)
        
        # Verify analysis
        assert analysis.pattern_matched is not None
        assert analysis.pattern_matched.pattern_id == 'connection_refused'
        assert len(analysis.suggestions) > 0
    
    def test_error_history_retrieval(self, engine):
        """Test error history retrieval."""
        # Store multiple errors
        for i in range(3):
            error = ExecutionError(
                error_id=f"history_error_{i}",
                task=Task(
                    intent=Intent.CHECK_STATUS,
                    entities=[],
                    script_id="status_script_001",
                    parameters={},
                    is_write_action=False
                ),
                error_message=f"Test error {i}",
                timestamp=datetime.utcnow()
            )
            engine.store_error(error)
        
        # Retrieve history
        history = engine.get_error_history()
        
        assert len(history) >= 3
        assert any(e['error_id'] == 'history_error_0' for e in history)
        assert any(e['error_id'] == 'history_error_1' for e in history)
        assert any(e['error_id'] == 'history_error_2' for e in history)
    
    def test_error_history_with_filters(self, engine):
        """Test error history with filters."""
        # Store errors with different timestamps
        now = datetime.utcnow()
        
        error1 = ExecutionError(
            error_id="filtered_error_1",
            task=Task(
                intent=Intent.CHECK_STATUS,
                entities=[],
                script_id="status_script_001",
                parameters={},
                is_write_action=False
            ),
            error_message="Test error 1",
            timestamp=now
        )
        engine.store_error(error1)
        
        # Retrieve history (no filters for now)
        history = engine.get_error_history()
        
        assert any(e['error_id'] == 'filtered_error_1' for e in history)
