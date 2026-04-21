"""
Script Registry for the Nexus Intelligent Chatbot System.

Manages registration and metadata of executable scripts with admin authorization.
"""

from typing import Optional, List
from datetime import datetime

from nexus.database import db, DatabaseError
from nexus.models import (
    Script, ScriptLanguage, Intent, Parameter, User, UserRole
)


class ScriptRegistryError(Exception):
    """Raised when script registry operations fail."""
    pass


class ScriptRegistry:
    """
    Manages script registration and metadata.
    
    Provides CRUD operations for scripts with admin authorization checks.
    """
    
    def __init__(self, database: db = None):
        """
        Initialize Script Registry.
        
        Args:
            database: Database instance. Uses global db if not provided.
        """
        self.db = database or db
    
    def _check_admin_authorization(self, user: User) -> bool:
        """
        Check if user has admin authorization.
        
        Args:
            user: User to check
            
        Returns:
            True if user is ADMIN, False otherwise
        """
        return user.role == UserRole.ADMIN
    
    def register_script(self, script: Script, admin_user: User) -> bool:
        """
        Register a new script (admin only).
        
        Args:
            script: Script with metadata
            admin_user: Administrator registering the script
            
        Returns:
            True if successful
            
        Raises:
            ScriptRegistryError: If user is not authorized or registration fails
        """
        if not self._check_admin_authorization(admin_user):
            raise ScriptRegistryError(
                f"User {admin_user.email} is not authorized to register scripts. "
                "Only ADMIN users can register scripts."
            )
        
        try:
            success = self.db.insert_script(script)
            if not success:
                raise ScriptRegistryError(
                    f"Failed to register script '{script.script_id}'. "
                    "A script with this ID may already exist."
                )
            return True
        except DatabaseError as e:
            raise ScriptRegistryError(f"Database error during registration: {str(e)}") from e
    
    def get_script(self, script_id: str) -> Optional[Script]:
        """
        Retrieve a script by ID.
        
        Args:
            script_id: Script identifier
            
        Returns:
            Script object or None if not found
        """
        return self.db.get_script(script_id)
    
    def find_scripts_by_intent(self, intent: Intent) -> List[Script]:
        """
        Find all scripts mapped to an intent.
        
        Args:
            intent: Intent to search for
            
        Returns:
            List of matching scripts
        """
        return self.db.find_scripts_by_intent(intent)
    
    def unregister_script(self, script_id: str, admin_user: User) -> bool:
        """
        Remove a script (admin only).
        
        Args:
            script_id: Script identifier
            admin_user: Administrator performing the removal
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            ScriptRegistryError: If user is not authorized
        """
        if not self._check_admin_authorization(admin_user):
            raise ScriptRegistryError(
                f"User {admin_user.email} is not authorized to unregister scripts. "
                "Only ADMIN users can unregister scripts."
            )
        
        try:
            return self.db.delete_script(script_id)
        except DatabaseError as e:
            raise ScriptRegistryError(f"Database error during deletion: {str(e)}") from e
    
    def list_all_scripts(self) -> List[Script]:
        """
        List all registered scripts.
        
        Returns:
            List of all scripts
        """
        return self.db.list_all_scripts()
    
    def find_script_by_id(self, script_id: str) -> Optional[Script]:
        """
        Find a script by its ID.
        
        This is an alias for get_script for consistency.
        
        Args:
            script_id: Script identifier
            
        Returns:
            Script object or None if not found
        """
        return self.get_script(script_id)
    
    def get_scripts_by_language(self, language: ScriptLanguage) -> List[Script]:
        """
        Get all scripts of a specific language.
        
        Args:
            language: Script language to filter by
            
        Returns:
            List of scripts with matching language
        """
        all_scripts = self.list_all_scripts()
        return [s for s in all_scripts if s.language == language]
    
    def get_read_only_scripts(self) -> List[Script]:
        """
        Get all read-only scripts.
        
        Returns:
            List of read-only scripts
        """
        all_scripts = self.list_all_scripts()
        return [s for s in all_scripts if s.is_read_only]
    
    def get_write_scripts(self) -> List[Script]:
        """
        Get all write-action scripts.
        
        Returns:
            List of write-action scripts
        """
        all_scripts = self.list_all_scripts()
        return [s for s in all_scripts if not s.is_read_only]
