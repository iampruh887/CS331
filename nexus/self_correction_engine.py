"""
Self-Correction Engine for the Nexus Intelligent Chatbot System.

Analyzes execution errors, identifies patterns, and suggests fixes
based on historical error data.
"""

import re
import uuid
from datetime import datetime
from typing import Optional, List

from nexus.database import db, DatabaseError
from nexus.models import (
    ExecutionError, ErrorPattern, ErrorAnalysis, Task, ExecutionResult
)
from nexus.config import config


class SelfCorrectionEngineError(Exception):
    """Raised when self-correction analysis fails."""
    pass


class SelfCorrectionEngine:
    """
    Analyzes execution errors and suggests fixes based on historical patterns.
    
    Stores errors in the database, identifies known error patterns using regex
    matching, and generates fix suggestions based on matched patterns.
    """
    
    # Default error patterns to seed in the database
    DEFAULT_ERROR_PATTERNS = [
        {
            'pattern_id': 'connection_refused',
            'pattern_regex': r'Connection refused|Connection refused by host|ECONNREFUSED|Connection timed out',
            'description': 'Connection to remote host or service was refused',
            'common_causes': [
                'Service is not running',
                'Firewall blocking connection',
                'Wrong port or host configured',
                'Service crashed or failed to start'
            ],
            'suggested_fixes': [
                'Check if the service is running: systemctl status <service>',
                'Restart the service: systemctl restart <service>',
                'Verify network connectivity to the host',
                'Check firewall rules and port availability'
            ]
        },
        {
            'pattern_id': 'permission_denied',
            'pattern_regex': r'Permission denied|EACCES|Operation not permitted|Access denied',
            'description': 'Insufficient permissions to perform operation',
            'common_causes': [
                'Running without sufficient privileges',
                'File or directory permissions incorrect',
                'User not in required group',
                'SELinux/AppArmor blocking access'
            ],
            'suggested_fixes': [
                'Run with sudo: sudo <command>',
                'Check file permissions: ls -l <file>',
                'Fix permissions: chmod +x <file> or chown user:group <file>',
                'Check SELinux status: sestatus'
            ]
        },
        {
            'pattern_id': 'file_not_found',
            'pattern_regex': r'File not found|No such file or directory|ENOENT|command not found',
            'description': 'Specified file, directory, or command does not exist',
            'common_causes': [
                'File or directory path is incorrect',
                'Command not in PATH',
                'File was deleted or moved',
                'Typo in filename or command'
            ],
            'suggested_fixes': [
                'Verify file exists: ls -l <path>',
                'Check current directory: pwd',
                'Find file: find / -name "<filename>" 2>/dev/null',
                'Check PATH: echo $PATH'
            ]
        },
        {
            'pattern_id': 'out_of_memory',
            'pattern_regex': r'Out of memory|OOM|Cannot allocate memory|Memory allocation failed',
            'description': 'System ran out of memory during operation',
            'common_causes': [
                'Insufficient system memory',
                'Memory leak in application',
                'Process requires more memory than available',
                'Memory limits too restrictive'
            ],
            'suggested_fixes': [
                'Check memory usage: free -h',
                'Check memory-intensive processes: top -o %MEM',
                'Increase system memory or swap space',
                'Optimize application memory usage'
            ]
        },
        {
            'pattern_id': 'disk_full',
            'pattern_regex': r'No space left on device|Disk full|ENOSPC|Out of disk space',
            'description': 'Disk or partition is full',
            'common_causes': [
                'Disk partition is full',
                'Inode exhaustion',
                'Log files not rotated',
                'Temporary files not cleaned up'
            ],
            'suggested_fixes': [
                'Check disk space: df -h',
                'Check inodes: df -i',
                'Find large files: find / -type f -size +100M 2>/dev/null',
                'Clean up logs: journalctl --vacuum-time=7d'
            ]
        },
        {
            'pattern_id': 'timeout',
            'pattern_regex': r'Timeout|Operation timed out|ETIMEDOUT|Deadline exceeded',
            'description': 'Operation exceeded allowed time limit',
            'common_causes': [
                'Network latency or connectivity issues',
                'Service is slow or unresponsive',
                'Timeout value too short for operation',
                'Resource contention or lock wait'
            ],
            'suggested_fixes': [
                'Increase timeout value',
                'Check network connectivity',
                'Check service health and logs',
                'Optimize slow operations'
            ]
        },
        {
            'pattern_id': 'invalid_input',
            'pattern_regex': r'Invalid input|Invalid argument|EINVAL|Bad request|Malformed',
            'description': 'Input provided to operation was invalid',
            'common_causes': [
                'Invalid parameter values',
                'Malformed JSON or XML',
                'Type mismatch in parameters',
                'Required field missing'
            ],
            'suggested_fixes': [
                'Validate input parameters',
                'Check API documentation for correct format',
                'Add required fields to request',
                'Use proper data types'
            ]
        },
        {
            'pattern_id': 'authentication_failed',
            'pattern_regex': r'Authentication failed|Unauthorized|401|403|Invalid credentials|Access denied',
            'description': 'Authentication or authorization failed',
            'common_causes': [
                'Invalid or expired credentials',
                'Insufficient permissions',
                'Token expired or revoked',
                'User account disabled'
            ],
            'suggested_fixes': [
                'Re-authenticate to obtain new credentials',
                'Check user permissions and roles',
                'Refresh expired tokens',
                'Verify user account status'
            ]
        },
        {
            'pattern_id': 'service_unavailable',
            'pattern_regex': r'Service unavailable|503|Service not responding|Backend error',
            'description': 'Target service is unavailable',
            'common_causes': [
                'Service is down or restarting',
                'Backend dependency failed',
                'Load balancer health check failed',
                'Service overloaded'
            ],
            'suggested_fixes': [
                'Check service status: systemctl status <service>',
                'Restart the service: systemctl restart <service>',
                'Check service logs for errors',
                'Check dependent services'
            ]
        },
        {
            'pattern_id': 'database_error',
            'pattern_regex': r'Database error|SQL error|Connection to database failed|Query failed',
            'description': 'Database operation failed',
            'common_causes': [
                'Database server not reachable',
                'Connection pool exhausted',
                'Invalid SQL query',
                'Database schema mismatch'
            ],
            'suggested_fixes': [
                'Check database server status',
                'Check connection pool settings',
                'Review SQL query syntax',
                'Check database logs'
            ]
        }
    ]
    
    def __init__(self, database=None):
        """
        Initialize Self-Correction Engine.
        
        Args:
            database: Database instance. Uses global if not provided.
        """
        self.db = database or db
        self._seed_default_patterns()
    
    def _seed_default_patterns(self):
        """Seed the database with default error patterns if not already present."""
        existing_patterns = self.db.get_all_error_patterns()
        existing_ids = {p.pattern_id for p in existing_patterns}
        
        for pattern in self.DEFAULT_ERROR_PATTERNS:
            if pattern['pattern_id'] not in existing_ids:
                error_pattern = ErrorPattern(
                    pattern_id=pattern['pattern_id'],
                    pattern_regex=pattern['pattern_regex'],
                    description=pattern['description'],
                    common_causes=pattern['common_causes'],
                    suggested_fixes=pattern['suggested_fixes']
                )
                self.db.insert_error_pattern(error_pattern)
    
    def analyze_error(self, error: ExecutionError) -> ErrorAnalysis:
        """
        Analyze error and suggest fixes.
        
        Args:
            error: Execution error details
            
        Returns:
            ErrorAnalysis with suggestions
        """
        # Identify pattern
        pattern = self._identify_pattern(error)
        
        # Generate suggestions
        suggestions = self._generate_suggestions(pattern) if pattern else []
        
        # Calculate confidence based on pattern match quality
        confidence = self._calculate_confidence(pattern, error) if pattern else 0.0
        
        return ErrorAnalysis(
            error_id=error.error_id,
            pattern_matched=pattern,
            suggestions=suggestions,
            confidence=confidence
        )
    
    def _identify_pattern(self, error: ExecutionError) -> Optional[ErrorPattern]:
        """
        Identify known error pattern from error message.
        
        Args:
            error: Execution error to analyze
            
        Returns:
            Matching ErrorPattern or None if no match found
        """
        error_patterns = self.db.get_all_error_patterns()
        error_message = error.error_message or ""
        
        for pattern in error_patterns:
            try:
                if re.search(pattern.pattern_regex, error_message, re.IGNORECASE):
                    return pattern
            except re.error:
                # Skip invalid regex patterns
                continue
        
        return None
    
    def _generate_suggestions(self, pattern: ErrorPattern) -> List[str]:
        """
        Generate fix suggestions based on matched pattern.
        
        Args:
            pattern: Matched error pattern
            
        Returns:
            List of suggested fixes
        """
        return pattern.suggested_fixes.copy()
    
    def _calculate_confidence(self, pattern: ErrorPattern, error: ExecutionError) -> float:
        """
        Calculate confidence score for pattern match.
        
        Args:
            pattern: Matched error pattern
            error: Execution error
            
        Returns:
            Confidence score between 0 and 1
        """
        # Base confidence on pattern match quality
        error_message = error.error_message or ""
        
        # Check if there's an exact match (high confidence)
        if pattern.pattern_regex in error_message:
            return 0.9
        
        # Check for strong pattern match (medium-high confidence)
        match = re.search(pattern.pattern_regex, error_message, re.IGNORECASE)
        if match and len(match.group(0)) > 10:
            return 0.7
        
        # Check for partial match (medium confidence)
        if match:
            return 0.5
        
        # Default confidence for pattern-based analysis
        return 0.3
    
    def store_error(self, error: ExecutionError) -> bool:
        """
        Store error in database for pattern learning.
        
        Args:
            error: Execution error to store
            
        Returns:
            True if stored successfully
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO error_logs (
                        error_id, task_json, error_message, stack_trace, timestamp
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    error.error_id,
                    self._serialize_task(error.task),
                    error.error_message or "",
                    error.stack_trace or "",
                    error.timestamp.isoformat()
                ))
                return True
        except DatabaseError as e:
            raise SelfCorrectionEngineError(f"Failed to store error: {str(e)}") from e
    
    def _serialize_task(self, task: Task) -> str:
        """
        Serialize task to JSON string for storage.
        
        Args:
            task: Task to serialize
            
        Returns:
            JSON string representation
        """
        import json
        
        return json.dumps({
            'intent': task.intent.value,
            'entities': [
                {
                    'entity_type': e.entity_type.value,
                    'value': e.value,
                    'confidence': e.confidence
                } for e in task.entities
            ],
            'script_id': task.script_id,
            'parameters': task.parameters,
            'is_write_action': task.is_write_action
        })
    
    def get_error_history(self, user_id: Optional[str] = None, 
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None) -> List[dict]:
        """
        Retrieve error history from database.
        
        Args:
            user_id: Filter by user ID
            start_date: Filter by start date (ISO format)
            end_date: Filter by end date (ISO format)
            
        Returns:
            List of error log entries
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM error_logs WHERE 1=1"
            params = []
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date)
            
            query += " ORDER BY timestamp DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
