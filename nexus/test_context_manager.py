"""
Property-based tests for the Context Manager.

Tests:
- Context size invariant
- Reference resolution
- User context isolation

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis import HealthCheck
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nexus.context_manager import ContextManager
from nexus.models import Message, Intent, EntityType, Entity


class TestContextSizeInvariant:
    """Property tests for context size management."""
    
    @pytest.mark.property_test
    @pytest.mark.property_8
    @given(
        num_messages=st.integers(min_value=1, max_value=10),
        user_id=st.text(min_size=3, max_size=20)
    )
    @settings(max_examples=30, deadline=5000, suppress_health_check=[HealthCheck.too_slow])
    def test_context_size_invariant(self, num_messages, user_id):
        """
        Property 8: Context size invariant
        
        For any user session, after adding N messages (where N > 3), the Context Manager
        should maintain exactly 3 messages (the most recent ones).
        **Validates: Requirements 3.1, 3.3**
        """
        manager = ContextManager(max_context_size=3)
        
        # Add N messages to context
        for i in range(num_messages):
            message = Message(
                text=f"Message {i}",
                intent=Intent.CHECK_STATUS,
                entities=[],
                timestamp=datetime.now() - timedelta(seconds=i)
            )
            manager.update_context(user_id, message)
        
        # Get the context
        history = manager.get_context(user_id)
        
        # Verify context size is exactly 3 (or less if N < 3)
        expected_size = min(num_messages, 3)
        assert history is not None
        assert len(history.messages) == expected_size
    
    @pytest.mark.property_test
    @pytest.mark.property_8
    @given(
        user_id=st.text(min_size=3, max_size=20),
        message_count=st.integers(min_value=4, max_value=20)
    )
    @settings(max_examples=20, deadline=5000)
    def test_pruning_keeps_most_recent(self, user_id, message_count):
        """
        Property: Context pruning should keep the most recent messages.
        
        When more than 3 messages are added, the Context Manager should
        keep only the 3 most recent messages and discard older ones.
        **Validates: Requirements 3.1, 3.3**
        """
        manager = ContextManager(max_context_size=3)
        
        # Add messages with different timestamps
        base_time = datetime.now()
        for i in range(message_count):
            message = Message(
                text=f"Message {i}",
                intent=Intent.QUERY_METRICS,
                entities=[],
                timestamp=base_time - timedelta(seconds=message_count - i)
            )
            manager.update_context(user_id, message)
        
        # Get the context
        history = manager.get_context(user_id)
        
        # Verify we have exactly 3 messages
        assert history is not None
        assert len(history.messages) == 3
        
        # Verify the messages are the most recent ones
        # The first message in the list should be the oldest of the 3 kept
        # The last message should be the most recent
        for i, msg in enumerate(history.messages):
            expected_text = f"Message {message_count - 3 + i}"
            assert msg.text == expected_text


class TestReferenceResolution:
    """Property tests for reference resolution."""
    
    @pytest.mark.property_test
    @pytest.mark.property_9
    @given(
        server_name=st.text(min_size=3, max_size=20),
        user_id=st.text(min_size=3, max_size=20)
    )
    @settings(max_examples=20, deadline=5000)
    def test_reference_resolution(self, server_name, user_id):
        """
        Property 9: Reference resolution
        
        For any user session with stored entities, when a command contains a reference
        ("it", "that server"), the Context Manager should resolve it to the most recent
        entity of the matching type from the last 3 messages.
        **Validates: Requirements 3.2**
        """
        manager = ContextManager(max_context_size=3)
        
        # Add a message with a server entity
        server_entity = Entity(
            entity_type=EntityType.SERVER,
            value=server_name,
            confidence=0.9
        )
        
        message = Message(
            text=f"Check {server_name}",
            intent=Intent.CHECK_STATUS,
            entities=[server_entity],
            timestamp=datetime.now()
        )
        manager.update_context(user_id, message)
        
        # Resolve the reference "it" to a server entity
        resolved = manager.resolve_reference(user_id, "it", EntityType.SERVER)
        
        # Verify the reference was resolved
        assert resolved is not None
        assert resolved.entity_type == EntityType.SERVER
        assert resolved.value == server_name
    
    @pytest.mark.property_test
    @pytest.mark.property_9
    @given(
        service_name=st.text(min_size=3, max_size=20),
        user_id=st.text(min_size=3, max_size=20)
    )
    @settings(max_examples=20, deadline=5000)
    def test_reference_resolution_with_that(self, service_name, user_id):
        """
        Property: Reference resolution should work with "that" references.
        
        For commands containing "that service" or similar references,
        the Context Manager should resolve to the most recent matching entity.
        **Validates: Requirements 3.2**
        """
        manager = ContextManager(max_context_size=3)
        
        # Add a message with a service entity
        service_entity = Entity(
            entity_type=EntityType.SERVICE,
            value=service_name,
            confidence=0.85
        )
        
        message = Message(
            text=f"Restart {service_name}",
            intent=Intent.RESTART_SERVICE,
            entities=[service_entity],
            timestamp=datetime.now()
        )
        manager.update_context(user_id, message)
        
        # Resolve the reference "that service"
        resolved = manager.resolve_reference(user_id, "that service", EntityType.SERVICE)
        
        # Verify the reference was resolved
        assert resolved is not None
        assert resolved.entity_type == EntityType.SERVICE
        assert resolved.value == service_name
    
    @pytest.mark.property_test
    @pytest.mark.property_9
    @given(
        user_id=st.text(min_size=3, max_size=20)
    )
    @settings(max_examples=10)
    def test_reference_resolution_no_context(self, user_id):
        """
        Property: Reference resolution should return None when no context exists.
        
        For a user without any conversation history, reference resolution
        should return None rather than crashing.
        **Validates: Requirements 3.2**
        """
        manager = ContextManager(max_context_size=3)
        
        # Try to resolve reference for user with no context
        resolved = manager.resolve_reference(user_id, "it", EntityType.SERVER)
        
        # Verify None is returned
        assert resolved is None
    
    @pytest.mark.property_test
    @pytest.mark.property_9
    @given(
        user_id=st.text(min_size=3, max_size=20)
    )
    @settings(max_examples=10)
    def test_reference_resolution_no_matching_entity(self, user_id):
        """
        Property: Reference resolution should return None when no matching entity exists.
        
        For a user with context but no entities of the requested type,
        reference resolution should return None.
        **Validates: Requirements 3.2**
        """
        manager = ContextManager(max_context_size=3)
        
        # Add a message with a server entity
        server_entity = Entity(
            entity_type=EntityType.SERVER,
            value="web-server-01",
            confidence=0.9
        )
        
        message = Message(
            text="Check web-server-01",
            intent=Intent.CHECK_STATUS,
            entities=[server_entity],
            timestamp=datetime.now()
        )
        manager.update_context(user_id, message)
        
        # Try to resolve a service reference (but only server exists)
        resolved = manager.resolve_reference(user_id, "it", EntityType.SERVICE)
        
        # Verify None is returned (no matching entity type)
        assert resolved is None


class TestUserContextIsolation:
    """Property tests for user context isolation."""
    
    @pytest.mark.property_test
    @pytest.mark.property_10
    @given(
        user1_id=st.text(min_size=3, max_size=20).filter(lambda x: len(x) > 0),
        user2_id=st.text(min_size=3, max_size=20).filter(lambda x: len(x) > 0),
        message1=st.text(min_size=5, max_size=50),
        message2=st.text(min_size=5, max_size=50)
    )
    @settings(max_examples=20, deadline=5000)
    def test_user_context_isolation(self, user1_id, user2_id, message1, message2):
        """
        Property 10: User context isolation
        
        For any two different authenticated users, updating context for one user
        should not affect the context of the other user.
        **Validates: Requirements 3.5, 11.5**
        """
        # Ensure users are different
        assume(user1_id != user2_id)
        
        manager = ContextManager(max_context_size=3)
        
        # Add messages for user 1
        message1_obj = Message(
            text=message1,
            intent=Intent.CHECK_STATUS,
            entities=[],
            timestamp=datetime.now()
        )
        manager.update_context(user1_id, message1_obj)
        
        # Add messages for user 2
        message2_obj = Message(
            text=message2,
            intent=Intent.QUERY_METRICS,
            entities=[],
            timestamp=datetime.now()
        )
        manager.update_context(user2_id, message2_obj)
        
        # Verify user 1 context is not affected by user 2
        history1 = manager.get_context(user1_id)
        history2 = manager.get_context(user2_id)
        
        assert history1 is not None
        assert history2 is not None
        
        assert len(history1.messages) == 1
        assert len(history2.messages) == 1
        
        assert history1.messages[0].text == message1
        assert history2.messages[0].text == message2
    
    @pytest.mark.property_test
    @pytest.mark.property_10
    @given(
        user1_id=st.text(min_size=3, max_size=20).filter(lambda x: len(x) > 0),
        user2_id=st.text(min_size=3, max_size=20).filter(lambda x: len(x) > 0),
        num_messages=st.integers(min_value=4, max_value=10)
    )
    @settings(max_examples=15, deadline=5000)
    def test_user_context_pruning_independent(self, user1_id, user2_id, num_messages):
        """
        Property: Context pruning should be independent per user.
        
        When user 1's context is pruned to 3 messages, user 2's context
        should remain unchanged.
        **Validates: Requirements 3.5, 11.5**
        """
        # Ensure users are different
        assume(user1_id != user2_id)
        
        manager = ContextManager(max_context_size=3)
        
        # Add messages for user 1 (more than 3 to trigger pruning)
        for i in range(num_messages):
            message = Message(
                text=f"User1 Message {i}",
                intent=Intent.CHECK_STATUS,
                entities=[],
                timestamp=datetime.now() - timedelta(seconds=i)
            )
            manager.update_context(user1_id, message)
        
        # Add messages for user 2 (less than 3)
        for i in range(2):
            message = Message(
                text=f"User2 Message {i}",
                intent=Intent.QUERY_METRICS,
                entities=[],
                timestamp=datetime.now() - timedelta(seconds=i)
            )
            manager.update_context(user2_id, message)
        
        # Verify user 1 has exactly 3 messages (pruned)
        history1 = manager.get_context(user1_id)
        assert history1 is not None
        assert len(history1.messages) == 3
        
        # Verify user 2 still has 2 messages (not pruned)
        history2 = manager.get_context(user2_id)
        assert history2 is not None
        assert len(history2.messages) == 2


class TestClearContext:
    """Property tests for context clearing."""
    
    @pytest.mark.property_test
    @given(
        user_id=st.text(min_size=3, max_size=20),
        num_messages=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=20, deadline=5000)
    def test_clear_context(self, user_id, num_messages):
        """
        Property: Clear context should remove all messages for a user.
        
        For any user with context, calling clear_context should remove
        all stored messages and return True.
        **Validates: Requirements 3.4**
        """
        manager = ContextManager(max_context_size=3)
        
        # Add messages for user
        for i in range(num_messages):
            message = Message(
                text=f"Message {i}",
                intent=Intent.CHECK_STATUS,
                entities=[],
                timestamp=datetime.now()
            )
            manager.update_context(user_id, message)
        
        # Verify context exists
        history = manager.get_context(user_id)
        assert history is not None
        assert len(history.messages) > 0
        
        # Clear context
        result = manager.clear_context(user_id)
        
        # Verify context was cleared
        assert result is True
        history = manager.get_context(user_id)
        assert history is None
    
    @pytest.mark.property_test
    @given(
        user_id=st.text(min_size=3, max_size=20)
    )
    @settings(max_examples=10)
    def test_clear_nonexistent_context(self, user_id):
        """
        Property: Clearing non-existent context should return False.
        
        For a user without any context, clear_context should return False
        and not raise an error.
        **Validates: Requirements 3.4**
        """
        manager = ContextManager(max_context_size=3)
        
        # Try to clear context for user with no context
        result = manager.clear_context(user_id)
        
        # Verify False is returned
        assert result is False


class TestMultipleEntityTypes:
    """Property tests for multiple entity types in context."""
    
    @pytest.mark.property_test
    @given(
        server_name=st.text(min_size=3, max_size=20),
        service_name=st.text(min_size=3, max_size=20),
        user_id=st.text(min_size=3, max_size=20)
    )
    @settings(max_examples=15, deadline=5000)
    def test_multiple_entity_types_in_context(self, server_name, service_name, user_id):
        """
        Property: Context should support multiple entity types.
        
        For a user with messages containing different entity types,
        reference resolution should correctly match by entity type.
        **Validates: Requirements 3.2**
        """
        manager = ContextManager(max_context_size=3)
        
        # Add message with both server and service entities
        entities = [
            Entity(entity_type=EntityType.SERVER, value=server_name, confidence=0.9),
            Entity(entity_type=EntityType.SERVICE, value=service_name, confidence=0.85)
        ]
        
        message = Message(
            text=f"Check {service_name} on {server_name}",
            intent=Intent.CHECK_STATUS,
            entities=entities,
            timestamp=datetime.now()
        )
        manager.update_context(user_id, message)
        
        # Resolve server reference
        resolved_server = manager.resolve_reference(user_id, "it", EntityType.SERVER)
        assert resolved_server is not None
        assert resolved_server.value == server_name
        
        # Resolve service reference
        resolved_service = manager.resolve_reference(user_id, "it", EntityType.SERVICE)
        assert resolved_service is not None
        assert resolved_service.value == service_name
    
    @pytest.mark.property_test
    @given(
        user_id=st.text(min_size=3, max_size=20),
        num_messages=st.integers(min_value=2, max_value=4)
    )
    @settings(max_examples=15, deadline=5000)
    def test_reference_resolves_to_most_recent(self, user_id, num_messages):
        """
        Property: Reference resolution should return the most recent matching entity.
        
        When a user has multiple messages with entities of the same type,
        reference resolution should return the most recent one.
        **Validates: Requirements 3.2**
        """
        manager = ContextManager(max_context_size=3)
        
        # Add multiple messages with different server entities
        base_time = datetime.now()
        expected_server = None
        
        for i in range(num_messages):
            server_name = f"server-{i}"
            entity = Entity(
                entity_type=EntityType.SERVER,
                value=server_name,
                confidence=0.9
            )
            
            message = Message(
                text=f"Check {server_name}",
                intent=Intent.CHECK_STATUS,
                entities=[entity],
                timestamp=base_time - timedelta(seconds=num_messages - i)
            )
            manager.update_context(user_id, message)
            
            # Track the most recent server
            if i == num_messages - 1:
                expected_server = server_name
        
        # Resolve reference - should get the most recent server
        resolved = manager.resolve_reference(user_id, "it", EntityType.SERVER)
        
        assert resolved is not None
        assert resolved.value == expected_server


class TestEdgeCases:
    """Property tests for edge cases."""
    
    @pytest.mark.property_test
    @given(
        user_id=st.text(min_size=3, max_size=20)
    )
    @settings(max_examples=10)
    def test_empty_context_retrieval(self, user_id):
        """
        Property: Getting empty context should return None.
        
        For a user with no context, get_context should return None
        rather than an empty MessageHistory.
        **Validates: Requirements 3.1**
        """
        manager = ContextManager(max_context_size=3)
        
        # Get context for user with no messages
        history = manager.get_context(user_id)
        
        # Verify None is returned
        assert history is None
    
    @pytest.mark.property_test
    @given(
        user_id=st.text(min_size=3, max_size=20),
        reference=st.text(min_size=1, max_size=20)
    )
    @settings(max_examples=10)
    def test_reference_resolution_with_no_entities(self, user_id, reference):
        """
        Property: Reference resolution should handle messages without entities.
        
        For a user with messages that don't contain entities, reference
        resolution should return None.
        **Validates: Requirements 3.2**
        """
        manager = ContextManager(max_context_size=3)
        
        # Add message with no entities
        message = Message(
            text="Just a message without entities",
            intent=Intent.CHECK_STATUS,
            entities=[],
            timestamp=datetime.now()
        )
        manager.update_context(user_id, message)
        
        # Try to resolve reference
        resolved = manager.resolve_reference(user_id, reference, EntityType.SERVER)
        
        # Verify None is returned
        assert resolved is None
    
    @pytest.mark.property_test
    @given(
        user_id=st.text(min_size=3, max_size=20),
        entity_type=st.sampled_from(list(EntityType))
    )
    @settings(max_examples=10)
    def test_reference_resolution_with_any_entity_type(self, user_id, entity_type):
        """
        Property: Reference resolution should work with any entity type.
        
        For any entity type, reference resolution should correctly
        match entities of that type.
        **Validates: Requirements 3.2**
        """
        manager = ContextManager(max_context_size=3)
        
        # Add message with entity of the specified type
        entity = Entity(
            entity_type=entity_type,
            value=f"test-value-{entity_type.value}",
            confidence=0.9
        )
        
        message = Message(
            text=f"Test {entity_type.value}",
            intent=Intent.CHECK_STATUS,
            entities=[entity],
            timestamp=datetime.now()
        )
        manager.update_context(user_id, message)
        
        # Resolve reference
        resolved = manager.resolve_reference(user_id, "it", entity_type)
        
        # Verify the entity was resolved
        assert resolved is not None
        assert resolved.entity_type == entity_type
