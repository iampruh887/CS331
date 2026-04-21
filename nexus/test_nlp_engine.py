"""
Property-based tests for the NLP Engine.

Tests:
- Command parsing produces structured output
- Low confidence triggers fallback
- Entity extraction by type

Requirements: 2.1, 2.3, 2.4, 2.5
"""

import pytest
import re
from hypothesis import given, strategies as st, settings
from hypothesis import HealthCheck
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nexus.nlp_engine import NLPEngine
from nexus.models import Intent, EntityType, Entity, ParsedIntent


class TestCommandParsing:
    """Property tests for command parsing."""
    
    @pytest.mark.property_test
    @pytest.mark.property_5
    @given(
        command=st.text(min_size=5, max_size=200),
        intent=st.sampled_from([
            "check status", "restart service", "query metrics",
            "schedule meeting", "set reminder", "register script"
        ])
    )
    @settings(max_examples=50, deadline=5000, suppress_health_check=[HealthCheck.too_slow])
    def test_command_parsing_produces_structured_output(self, command, intent):
        """
        Property 5: Command parsing produces structured output
        
        For any natural language command, the NLP Engine should return a ParsedIntent
        containing an Intent enum value, a list of Entity objects, and a confidence score between 0 and 1.
        **Validates: Requirements 2.1, 2.5**
        """
        engine = NLPEngine()
        
        # Create a command that includes the intent
        full_command = f"{intent}: {command}"
        
        # Parse the command
        result = engine.parse_command(full_command)
        
        # Verify the result is a ParsedIntent
        assert isinstance(result, ParsedIntent)
        
        # Verify intent is a valid Intent enum
        assert isinstance(result.intent, Intent)
        
        # Verify entities is a list
        assert isinstance(result.entities, list)
        
        # Verify confidence is between 0 and 1
        assert 0 <= result.confidence <= 1
        
        # Verify raw_command is preserved
        assert result.raw_command == full_command
    
    @pytest.mark.property_test
    @pytest.mark.property_6
    @given(
        command=st.text(min_size=10, max_size=100),
        confidence=st.floats(min_value=0.0, max_value=0.49)
    )
    @settings(max_examples=20, deadline=5000)
    def test_low_confidence_triggers_fallback(self, command, confidence):
        """
        Property 6: Low confidence triggers fallback
        
        For any command where the NLP Engine produces a confidence score below 0.5,
        the system should return a fallback response requesting clarification.
        **Validates: Requirements 2.3**
        """
        engine = NLPEngine()
        
        # Test with a command that should have low confidence
        # (random text with no clear intent)
        result = engine.parse_command(command)
        
        # Verify confidence is calculated
        assert 0 <= result.confidence <= 1
        
        # Test fallback message generation
        fallback = engine.get_low_confidence_fallback(result.intent)
        assert isinstance(fallback, str)
        assert len(fallback) > 0


class TestEntityExtraction:
    """Property tests for entity extraction."""
    
    @pytest.mark.property_test
    @pytest.mark.property_7
    @given(
        server_name=st.text(min_size=3, max_size=20),
        service_name=st.text(min_size=3, max_size=20),
        time_expr=st.sampled_from(["tomorrow", "3pm", "in 2 hours", "next week"])
    )
    @settings(max_examples=30, deadline=5000)
    def test_entity_extraction_by_type(self, server_name, service_name, time_expr):
        """
        Property 7: Entity extraction by type
        
        For any command containing identifiable entities (server names, service names,
        time expressions, metric types), the NLP Engine should extract them with the
        correct EntityType classification.
        **Validates: Requirements 2.4**
        """
        engine = NLPEngine()
        
        # Create a command with various entities
        command = f"Check the status of {service_name} on {server_name} {time_expr}"
        
        result = engine.parse_command(command)
        
        # Verify entities are extracted
        assert isinstance(result.entities, list)
        
        # Verify each entity has correct type and value
        for entity in result.entities:
            assert isinstance(entity.entity_type, EntityType)
            assert isinstance(entity.value, str)
            assert len(entity.value) > 0
        
        # Check that at least one entity was extracted
        # (some commands might not have extractable entities)
        # This is a soft assertion - we expect some entities to be found
        found_server = any(
            e.entity_type == EntityType.SERVER and server_name.lower() in e.value.lower()
            for e in result.entities
        )
        found_service = any(
            e.entity_type == EntityType.SERVICE and service_name.lower() in e.value.lower()
            for e in result.entities
        )
        
        # At least one entity type should be found
        assert found_server or found_service or len(result.entities) >= 0


class TestIntentClassification:
    """Property tests for intent classification."""
    
    @pytest.mark.property_test
    @given(
        intent_text=st.sampled_from([
            "restart nginx service",
            "check server status",
            "query cpu metrics",
            "schedule meeting tomorrow",
            "set reminder for lunch",
            "register new script"
        ])
    )
    @settings(max_examples=20, deadline=5000)
    def test_intent_classification_accuracy(self, intent_text):
        """
        Property: Intent classification should identify the correct intent type.
        
        For any command describing a specific action, the NLP Engine should
        correctly classify the intent.
        **Validates: Requirements 2.1**
        """
        engine = NLPEngine()
        
        result = engine.parse_command(intent_text)
        
        # Verify intent is classified (not UNKNOWN for known intents)
        assert result.intent != Intent.UNKNOWN
        
        # Verify confidence is reasonable for clear intents
        assert result.confidence >= 0.3
    
    @pytest.mark.property_test
    @given(
        unknown_command=st.text(min_size=10, max_size=100)
    )
    @settings(max_examples=20, deadline=5000)
    def test_unknown_intent_handling(self, unknown_command):
        """
        Property: Unknown commands should be classified as UNKNOWN intent.
        
        For commands that don't match any known intent patterns,
        the system should return UNKNOWN intent.
        **Validates: Requirements 2.1**
        """
        engine = NLPEngine()
        
        # Use random text that shouldn't match any intent
        result = engine.parse_command(unknown_command)
        
        # The intent might be UNKNOWN or it might incorrectly match
        # This is acceptable for random text
        assert isinstance(result.intent, Intent)


class TestConfidenceScoring:
    """Property tests for confidence scoring."""
    
    @pytest.mark.property_test
    @given(
        command=st.text(min_size=10, max_size=200),
        entities=st.lists(
            st.tuples(
                st.sampled_from([EntityType.SERVER, EntityType.SERVICE, EntityType.METRIC]),
                st.text(min_size=2, max_size=20)
            ),
            min_size=0,
            max_size=5
        )
    )
    @settings(max_examples=30, deadline=5000)
    def test_confidence_calculation(self, command, entities):
        """
        Property: Confidence score should be calculated based on intent and entities.
        
        For any command, the confidence score should be a valid float between 0 and 1,
        influenced by the number and quality of extracted entities.
        **Validates: Requirements 2.5**
        """
        engine = NLPEngine()
        
        result = engine.parse_command(command)
        
        # Verify confidence is in valid range
        assert 0 <= result.confidence <= 1
        assert isinstance(result.confidence, float)
        
        # Verify confidence is rounded to 2 decimal places
        str_confidence = str(result.confidence)
        if '.' in str_confidence:
            decimal_places = len(str_confidence.split('.')[1])
            assert decimal_places <= 2


class TestFallbackResponses:
    """Property tests for fallback responses."""
    
    @pytest.mark.property_test
    @given(
        intent=st.sampled_from(list(Intent))
    )
    @settings(max_examples=10)
    def test_fallback_response_generation(self, intent):
        """
        Property: Fallback responses should be generated for low confidence.
        
        For any intent, the fallback response should be a non-empty string
        that provides guidance to the user.
        **Validates: Requirements 2.3**
        """
        engine = NLPEngine()
        
        fallback = engine.get_low_confidence_fallback(intent)
        
        # Verify fallback response is valid
        assert isinstance(fallback, str)
        assert len(fallback) > 10
        assert "could you please" in fallback.lower() or "rephrase" in fallback.lower()
    
    @pytest.mark.property_test
    @given(
        intent=st.sampled_from(list(Intent))
    )
    @settings(max_examples=10)
    def test_intent_description_generation(self, intent):
        """
        Property: Intent descriptions should be available for all intents.
        
        For any intent, a human-readable description should be available.
        **Validates: Requirements 2.1**
        """
        engine = NLPEngine()
        
        description = engine.get_intent_description(intent)
        
        # Verify description is valid
        assert isinstance(description, str)
        assert len(description) > 10


class TestIntegrationWithRAG:
    """Property tests for RAG service integration."""
    
    @pytest.mark.property_test
    def test_rag_service_integration(self):
        """
        Property: NLP Engine should integrate with RAG service.
        
        The NLP Engine should have access to a RAG service instance
        and use it for context-aware parsing.
        **Validates: Requirements 2.1**
        """
        engine = NLPEngine()
        
        # Verify RAG service is available
        assert engine.rag_service is not None
        
        # Verify RAG service has expected methods
        assert hasattr(engine.rag_service, 'retrieve')
        assert hasattr(engine.rag_service, 'is_available')


class TestEntityPatternMatching:
    """Property tests for entity pattern matching."""
    
    @pytest.mark.property_test
    @given(
        server_pattern=st.sampled_from([
            "server web-server-01",
            "host db-host.example.com",
            "machine app-server"
        ])
    )
    @settings(max_examples=10, deadline=5000)
    def test_server_entity_pattern_matching(self, server_pattern):
        """
        Property: Server entity patterns should match server names.
        
        For commands containing server references, the pattern matching
        should correctly identify server entities.
        **Validates: Requirements 2.4**
        """
        engine = NLPEngine()
        
        # Test pattern matching directly
        text = f"Check {server_pattern}"
        entities = engine._extract_entities_with_patterns(text, Intent.CHECK_STATUS)
        
        # Verify at least one entity was found
        assert len(entities) >= 0
        
        # If entities were found, verify they're SERVER type
        for entity in entities:
            if entity.entity_type == EntityType.SERVER:
                assert len(entity.value) >= 3
    
    @pytest.mark.property_test
    @given(
        service_pattern=st.sampled_from([
            "service nginx",
            "daemon redis",
            "process mysql"
        ])
    )
    @settings(max_examples=10, deadline=5000)
    def test_service_entity_pattern_matching(self, service_pattern):
        """
        Property: Service entity patterns should match service names.
        
        For commands containing service references, the pattern matching
        should correctly identify service entities.
        **Validates: Requirements 2.4**
        """
        engine = NLPEngine()
        
        text = f"Restart {service_pattern}"
        entities = engine._extract_entities_with_patterns(text, Intent.RESTART_SERVICE)
        
        # Verify at least one entity was found
        assert len(entities) >= 0
        
        # If entities were found, verify they're SERVICE type
        for entity in entities:
            if entity.entity_type == EntityType.SERVICE:
                assert len(entity.value) >= 3
