"""
Audit Logger for the Nexus Intelligent Chatbot System.

Provides immutable audit trail of all task executions with filtering capabilities.
"""

import uuid
from datetime import datetime
from typing import List, Optional
from nexus.database import Database, DatabaseError
from nexus.models import AuditEntry, LogFilter, ExecutionResult, Intent


class AuditLoggerError(Exception):
    """Raised when audit logging operations fail."""
    pass


class AuditLogger:
    """
    Audit Logger manages immutable audit trail of all executions.
    
    Provides functionality to:
    - Log task executions with full details
    - Retrieve logs with flexible filtering
    - Ensure immutability of audit records
    """
    
    def __init__(self, database: Optional[Database] = None):
        """
        Initialize Audit Logger.
        
        Args:
            database: Database instance. If None, uses global db instance.
        """
        from nexus.database import db as global_db
        self.db = database or global_db
    
    async def log_execution(self, entry: AuditEntry) -> bool:
        """
        Log execution to database (immutable).
        
        Creates an immutable audit log entry that cannot be modified or deleted.
        The entry is persisted immediately to ensure durability.
        
        Args:
            entry: AuditEntry with execution details
            
        Returns:
            True if logged successfully
            
        Raises:
            AuditLoggerError: If logging fails
        """
        try:
            # Validate entry
            if not entry.entry_id:
                raise AuditLoggerError("AuditEntry must have an entry_id")
            if not entry.user_id:
                raise AuditLoggerError("AuditEntry must have a user_id")
            if not entry.user_email:
                raise AuditLoggerError("AuditEntry must have a user_email")
            if not entry.command:
                raise AuditLoggerError("AuditEntry must have a command")
            
            # Insert into database (append-only)
            success = self.db.insert_audit_entry(entry)
            
            if not success:
                raise AuditLoggerError("Failed to insert audit entry")
            
            return True
            
        except DatabaseError as e:
            raise AuditLoggerError(f"Database error during audit logging: {str(e)}") from e
        except Exception as e:
            raise AuditLoggerError(f"Unexpected error during audit logging: {str(e)}") from e
    
    async def retrieve_logs(self, filter: LogFilter) -> List[AuditEntry]:
        """
        Retrieve logs with filtering.
        
        Supports filtering by:
        - User ID
        - Date range (start_date, end_date)
        - Intent type
        - Success status
        
        Args:
            filter: LogFilter with filter criteria
            
        Returns:
            List of matching audit entries
            
        Raises:
            AuditLoggerError: If retrieval fails
        """
        try:
            # Query database with filters
            rows = self.db.query_audit_logs(
                user_id=filter.user_id,
                start_date=filter.start_date,
                end_date=filter.end_date,
                intent=filter.intent,
                success_only=filter.success_only
            )
            
            # Convert rows to AuditEntry objects
            entries = []
            for row in rows:
                entry = self._row_to_audit_entry(row)
                entries.append(entry)
            
            return entries
            
        except DatabaseError as e:
            raise AuditLoggerError(f"Database error during log retrieval: {str(e)}") from e
        except Exception as e:
            raise AuditLoggerError(f"Unexpected error during log retrieval: {str(e)}") from e
    
    def _format_entry(self, entry: AuditEntry) -> str:
        """
        Format entry for database storage.
        
        Creates a human-readable string representation of the audit entry
        for logging and debugging purposes.
        
        Args:
            entry: AuditEntry to format
            
        Returns:
            Formatted string representation
        """
        status = "SUCCESS" if entry.result.success else "FAILURE"
        
        formatted = (
            f"[{entry.timestamp.isoformat()}] "
            f"User: {entry.user_email} ({entry.user_id}) | "
            f"Command: {entry.command} | "
            f"Intent: {entry.intent.value} | "
            f"Status: {status} | "
            f"Execution Time: {entry.execution_time_ms}ms"
        )
        
        if entry.result.error:
            formatted += f" | Error: {entry.result.error}"
        
        return formatted
    
    def _row_to_audit_entry(self, row: dict) -> AuditEntry:
        """
        Convert database row to AuditEntry object.
        
        Args:
            row: Database row as dictionary
            
        Returns:
            AuditEntry object
        """
        # Reconstruct ExecutionResult
        result = ExecutionResult(
            success=bool(row['success']),
            output=row['output'] or "",
            error=row['error'],
            execution_time_ms=row['execution_time_ms'],
            timestamp=datetime.fromisoformat(row['timestamp'])
        )
        
        # Create AuditEntry
        entry = AuditEntry(
            entry_id=row['entry_id'],
            user_id=row['user_id'],
            user_email=row['user_email'],
            command=row['command'],
            intent=Intent(row['intent']),
            result=result,
            timestamp=datetime.fromisoformat(row['timestamp']),
            execution_time_ms=row['execution_time_ms']
        )
        
        return entry
    
    def create_audit_entry(
        self,
        user_id: str,
        user_email: str,
        command: str,
        intent: Intent,
        result: ExecutionResult
    ) -> AuditEntry:
        """
        Create a new AuditEntry with generated UUID.
        
        Helper method to create audit entries with proper initialization.
        
        Args:
            user_id: User identifier
            user_email: User email address
            command: Command that was executed
            intent: Intent type
            result: Execution result
            
        Returns:
            New AuditEntry with generated entry_id and timestamp
        """
        return AuditEntry(
            entry_id=str(uuid.uuid4()),
            user_id=user_id,
            user_email=user_email,
            command=command,
            intent=intent,
            result=result,
            timestamp=datetime.utcnow(),
            execution_time_ms=result.execution_time_ms
        )
