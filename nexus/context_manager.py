"""
Context Manager for the Nexus Intelligent Chatbot System.

Maintains conversation context (last 3 messages) per user to resolve references
like "it", "that server", etc.
"""

from typing import Dict, List, Optional
from datetime import datetime
from nexus.models import Message, MessageHistory, Entity, EntityType, Intent


class ContextManager:
    """
    Manages conversation context for each user session.
    
    Stores the last 3 messages per user to enable reference resolution
    and maintain conversation history.
    """
    
    def __init__(self, max_context_size: int = 3):
        """
        Initialize context manager.
        
        Args:
            max_context_size: Maximum number of messages to store per user (default: 3)
        """
        self._context_store: Dict[str, MessageHistory] = {}
        self._max_context_size = max_context_size
    
    def get_context(self, user_id: str) -> Optional[MessageHistory]:
        """
        Retrieve user's conversation context.
        
        Args:
            user_id: User identifier
            
        Returns:
            MessageHistory for the user, or None if no context exists
        """
        return self._context_store.get(user_id)
    
    def update_context(self, user_id: str, message: Message) -> None:
        """
        Add message to user's context and prune old messages.
        
        Maintains a maximum of max_context_size messages by keeping only
        the most recent ones.
        
        Args:
            user_id: User identifier
            message: Message to add to context
        """
        if user_id not in self._context_store:
            self._context_store[user_id] = MessageHistory(user_id=user_id)
        
        history = self._context_store[user_id]
        history.add_message(message)
    
    def resolve_reference(
        self,
        user_id: str,
        reference: str,
        entity_type: EntityType
    ) -> Optional[Entity]:
        """
        Resolve contextual references like 'it', 'that server', etc.
        
        Searches through the user's recent messages (up to 3) to find
        the most recent entity of the specified type.
        
        Args:
            user_id: User identifier
            reference: Reference text (e.g., "it", "that server", "the service")
            entity_type: Type of entity being referenced
            
        Returns:
            Resolved Entity or None if not found
        """
        history = self._context_store.get(user_id)
        if not history:
            return None
        
        # Normalize reference for comparison
        reference_lower = reference.lower().strip()
        
        # Search through messages in reverse order (most recent first)
        for message in reversed(history.messages):
            for entity in message.entities:
                # Check if entity type matches
                if entity.entity_type == entity_type:
                    # For generic references like "it", "that", "this", "the", return the most recent
                    if reference_lower in ("it", "that", "this", "the"):
                        return entity
                    # For references like "that server", "the service", check if entity type matches
                    # The reference contains the entity type keyword
                    if entity_type.value in reference_lower:
                        return entity
                    # For specific references, check if the value matches
                    if self._matches_reference(entity.value, reference):
                        return entity
        
        return None
    
    def _matches_reference(self, entity_value: str, reference: str) -> bool:
        """
        Check if an entity value matches a reference text.
        
        Args:
            entity_value: The entity value from stored message
            reference: The reference text from current message
            
        Returns:
            True if the reference matches the entity value
        """
        reference_lower = reference.lower().strip()
        entity_lower = entity_value.lower()
        
        # Direct match
        if entity_lower == reference_lower:
            return True
        
        # Check if reference contains the entity value
        if entity_lower in reference_lower:
            return True
        
        # Check if entity value contains the reference
        if reference_lower in entity_lower:
            return True
        
        return False
    
    def clear_context(self, user_id: str) -> bool:
        """
        Clear user's context (e.g., on logout).
        
        Args:
            user_id: User identifier
            
        Returns:
            True if context was cleared, False if no context existed
        """
        if user_id in self._context_store:
            del self._context_store[user_id]
            return True
        return False
    
    def clear_all_contexts(self) -> int:
        """
        Clear all user contexts.
        
        Returns:
            Number of contexts cleared
        """
        count = len(self._context_store)
        self._context_store.clear()
        return count
    
    def get_user_ids(self) -> List[str]:
        """
        Get all user IDs with active context.
        
        Returns:
            List of user IDs
        """
        return list(self._context_store.keys())
    
    def get_message_count(self, user_id: str) -> int:
        """
        Get the number of messages in a user's context.
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of messages in context
        """
        history = self._context_store.get(user_id)
        return len(history.messages) if history else 0
