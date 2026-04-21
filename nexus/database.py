"""
Database management for the Nexus Intelligent Chatbot System.

Provides database connection, initialization, and helper functions for all tables.
"""

import sqlite3
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from contextlib import contextmanager
from nexus.config import config
from nexus.models import (
    Script, ScriptLanguage, Intent, Parameter,
    AuditEntry, ExecutionResult, ErrorPattern
)


class DatabaseError(Exception):
    """Raised when database operations fail."""
    pass


class Database:
    """
    Database manager for Nexus system.
    
    Handles connection management, table initialization, and CRUD operations.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file. If None, uses config.
        """
        self.db_path = db_path or config.get_database_path()
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.
        
        Yields:
            sqlite3.Connection: Database connection
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=config.DATABASE_OPERATION_TIMEOUT)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            yield conn
            conn.commit()
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            raise DatabaseError(f"Database operation failed: {str(e)}") from e
        finally:
            if conn:
                conn.close()
    
    def initialize_schema(self):
        """
        Initialize all database tables.
        
        Creates tables if they don't exist. Safe to call multiple times (idempotent).
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table (extends existing auth module)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    hashed_password TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    role TEXT DEFAULT 'GENERAL',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Scripts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scripts (
                    script_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    language TEXT NOT NULL,
                    mapped_intents TEXT NOT NULL,
                    parameters TEXT NOT NULL,
                    is_read_only BOOLEAN NOT NULL,
                    registered_by TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (registered_by) REFERENCES users(email)
                )
            """)
            
            # Audit logs table (immutable - no updates or deletes allowed)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    entry_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    user_email TEXT NOT NULL,
                    command TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    output TEXT,
                    error TEXT,
                    execution_time_ms INTEGER NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_email) REFERENCES users(email)
                )
            """)
            
            # Create trigger to prevent updates on audit_logs
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS prevent_audit_update
                BEFORE UPDATE ON audit_logs
                BEGIN
                    SELECT RAISE(ABORT, 'Audit logs are immutable and cannot be updated');
                END
            """)
            
            # Create trigger to prevent deletes on audit_logs
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS prevent_audit_delete
                BEFORE DELETE ON audit_logs
                BEGIN
                    SELECT RAISE(ABORT, 'Audit logs are immutable and cannot be deleted');
                END
            """)
            
            # Error logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS error_logs (
                    error_id TEXT PRIMARY KEY,
                    task_json TEXT NOT NULL,
                    error_message TEXT NOT NULL,
                    stack_trace TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Error patterns table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS error_patterns (
                    pattern_id TEXT PRIMARY KEY,
                    pattern_regex TEXT NOT NULL,
                    description TEXT NOT NULL,
                    common_causes TEXT NOT NULL,
                    suggested_fixes TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Confirmation prompts table (temporary storage)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS confirmation_prompts (
                    prompt_id TEXT PRIMARY KEY,
                    message TEXT NOT NULL,
                    task_json TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    expiry_time TIMESTAMP NOT NULL,
                    confirmed BOOLEAN,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    # Script Registry Operations
    
    def insert_script(self, script: Script) -> bool:
        """
        Insert a new script into the registry.
        
        Args:
            script: Script object to insert
            
        Returns:
            True if successful, False if duplicate script_id
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO scripts (
                        script_id, name, file_path, language, mapped_intents,
                        parameters, is_read_only, registered_by, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    script.script_id,
                    script.name,
                    script.file_path,
                    script.language.value,
                    json.dumps([intent.value for intent in script.mapped_intents]),
                    json.dumps([{
                        'name': p.name,
                        'type': p.type,
                        'required': p.required,
                        'description': p.description
                    } for p in script.parameters]),
                    script.is_read_only,
                    script.registered_by,
                    script.created_at.isoformat()
                ))
                return True
        except DatabaseError as e:
            # Check if it's a duplicate key error
            if "UNIQUE constraint failed" in str(e):
                return False
            raise
    
    def get_script(self, script_id: str) -> Optional[Script]:
        """
        Retrieve a script by ID.
        
        Args:
            script_id: Script identifier
            
        Returns:
            Script object or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scripts WHERE script_id = ?", (script_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_script(row)
            return None
    
    def find_scripts_by_intent(self, intent: Intent) -> List[Script]:
        """
        Find all scripts mapped to an intent.
        
        Args:
            intent: Intent to search for
            
        Returns:
            List of matching scripts
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scripts")
            rows = cursor.fetchall()
            
            scripts = []
            for row in rows:
                script = self._row_to_script(row)
                if intent in script.mapped_intents:
                    scripts.append(script)
            
            return scripts
    
    def delete_script(self, script_id: str) -> bool:
        """
        Delete a script from the registry.
        
        Args:
            script_id: Script identifier
            
        Returns:
            True if deleted, False if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM scripts WHERE script_id = ?", (script_id,))
            return cursor.rowcount > 0
    
    def list_all_scripts(self) -> List[Script]:
        """
        List all registered scripts.
        
        Returns:
            List of all scripts
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scripts")
            rows = cursor.fetchall()
            return [self._row_to_script(row) for row in rows]
    
    def _row_to_script(self, row: sqlite3.Row) -> Script:
        """Convert database row to Script object."""
        return Script(
            script_id=row['script_id'],
            name=row['name'],
            file_path=row['file_path'],
            language=ScriptLanguage(row['language']),
            mapped_intents=[Intent(i) for i in json.loads(row['mapped_intents'])],
            parameters=[Parameter(**p) for p in json.loads(row['parameters'])],
            is_read_only=bool(row['is_read_only']),
            registered_by=row['registered_by'],
            created_at=datetime.fromisoformat(row['created_at'])
        )
    
    # Audit Log Operations
    
    def insert_audit_entry(self, entry: AuditEntry) -> bool:
        """
        Insert an audit log entry (immutable).
        
        Args:
            entry: AuditEntry to insert
            
        Returns:
            True if successful
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_logs (
                    entry_id, user_id, user_email, command, intent,
                    success, output, error, execution_time_ms, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.entry_id,
                entry.user_id,
                entry.user_email,
                entry.command,
                entry.intent.value,
                entry.result.success,
                entry.result.output,
                entry.result.error,
                entry.execution_time_ms,
                entry.timestamp.isoformat()
            ))
            return True
    
    def query_audit_logs(
        self,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        intent: Optional[Intent] = None,
        success_only: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Query audit logs with filters.
        
        Args:
            user_id: Filter by user ID
            start_date: Filter by start date
            end_date: Filter by end date
            intent: Filter by intent
            success_only: Filter by success status
            
        Returns:
            List of audit log entries as dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM audit_logs WHERE 1=1"
            params = []
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())
            
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())
            
            if intent:
                query += " AND intent = ?"
                params.append(intent.value)
            
            if success_only is not None:
                query += " AND success = ?"
                params.append(success_only)
            
            query += " ORDER BY timestamp DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    # Error Pattern Operations
    
    def insert_error_pattern(self, pattern: ErrorPattern) -> bool:
        """
        Insert an error pattern.
        
        Args:
            pattern: ErrorPattern to insert
            
        Returns:
            True if successful
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO error_patterns (
                    pattern_id, pattern_regex, description,
                    common_causes, suggested_fixes
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                pattern.pattern_id,
                pattern.pattern_regex,
                pattern.description,
                json.dumps(pattern.common_causes),
                json.dumps(pattern.suggested_fixes)
            ))
            return True
    
    def get_all_error_patterns(self) -> List[ErrorPattern]:
        """
        Get all error patterns.
        
        Returns:
            List of all error patterns
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM error_patterns")
            rows = cursor.fetchall()
            
            patterns = []
            for row in rows:
                patterns.append(ErrorPattern(
                    pattern_id=row['pattern_id'],
                    pattern_regex=row['pattern_regex'],
                    description=row['description'],
                    common_causes=json.loads(row['common_causes']),
                    suggested_fixes=json.loads(row['suggested_fixes'])
                ))
            
            return patterns
    
    # Confirmation Prompt Operations
    
    def insert_confirmation_prompt(
        self,
        prompt_id: str,
        message: str,
        task_json: str,
        user_id: str,
        expiry_time: datetime
    ) -> bool:
        """
        Insert a confirmation prompt.
        
        Args:
            prompt_id: Unique prompt identifier
            message: Confirmation message
            task_json: JSON serialized task
            user_id: User identifier
            expiry_time: Expiry timestamp
            
        Returns:
            True if successful
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO confirmation_prompts (
                    prompt_id, message, task_json, user_id, expiry_time
                ) VALUES (?, ?, ?, ?, ?)
            """, (prompt_id, message, task_json, user_id, expiry_time.isoformat()))
            return True
    
    def get_confirmation_prompt(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a confirmation prompt by ID.
        
        Args:
            prompt_id: Prompt identifier
            
        Returns:
            Prompt data or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM confirmation_prompts WHERE prompt_id = ?",
                (prompt_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_confirmation_status(self, prompt_id: str, confirmed: bool) -> bool:
        """
        Update confirmation status.
        
        Args:
            prompt_id: Prompt identifier
            confirmed: Confirmation status
            
        Returns:
            True if updated
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE confirmation_prompts SET confirmed = ? WHERE prompt_id = ?",
                (confirmed, prompt_id)
            )
            return cursor.rowcount > 0


# Global database instance
db = Database()
