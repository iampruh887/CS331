"""
Database initialization and seeding script for Nexus Intelligent Chatbot System.

This script:
1. Initializes all database tables
2. Seeds error_patterns table with common patterns
3. Creates a default admin user
4. Registers sample scripts in the Script Registry

Run this script once during system setup:
    python -m nexus.init_db
"""

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from nexus.database import db
from nexus.models import (
    Script, ScriptLanguage, Intent, Parameter,
    ErrorPattern, UserRole
)
from auth.database import create_user, get_user, hash_password, IntegrityError


# Default admin credentials
DEFAULT_ADMIN_EMAIL = "admin@nexus.local"
DEFAULT_ADMIN_PASSWORD = "NexusAdmin123!"  # Should be changed in production


def initialize_database():
    """Initialize all database tables."""
    print("Initializing database schema...")
    try:
        db.initialize_schema()
        print("✓ Database schema initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize database schema: {e}")
        raise


def seed_error_patterns():
    """Seed error_patterns table with common infrastructure error patterns."""
    print("\nSeeding error patterns...")
    
    error_patterns = [
        ErrorPattern(
            pattern_id=str(uuid.uuid4()),
            pattern_regex=r"Connection refused|connection refused",
            description="Service connection refused",
            common_causes=[
                "Service is not running",
                "Service is listening on wrong port",
                "Firewall blocking connection"
            ],
            suggested_fixes=[
                "Check if the service is running: systemctl status <service>",
                "Verify the service is listening on the correct port: netstat -tlnp",
                "Check firewall rules: sudo ufw status"
            ]
        ),
        ErrorPattern(
            pattern_id=str(uuid.uuid4()),
            pattern_regex=r"Permission denied|permission denied",
            description="Permission denied error",
            common_causes=[
                "User lacks required permissions",
                "File/directory permissions are too restrictive",
                "SELinux or AppArmor policy blocking access"
            ],
            suggested_fixes=[
                "Check file permissions: ls -la <file>",
                "Change permissions if needed: chmod 755 <file>",
                "Check SELinux status: getenforce"
            ]
        ),
        ErrorPattern(
            pattern_id=str(uuid.uuid4()),
            pattern_regex=r"File not found|No such file or directory|cannot find",
            description="File or directory not found",
            common_causes=[
                "File path is incorrect",
                "File was deleted",
                "File is on a different system"
            ],
            suggested_fixes=[
                "Verify the file path: ls -la <path>",
                "Check if file exists in expected location",
                "Use find command to locate file: find / -name <filename>"
            ]
        ),
        ErrorPattern(
            pattern_id=str(uuid.uuid4()),
            pattern_regex=r"Timeout|timed out|timeout",
            description="Operation timeout",
            common_causes=[
                "Operation taking too long",
                "Network connectivity issues",
                "Remote service is slow or unresponsive"
            ],
            suggested_fixes=[
                "Increase timeout value if appropriate",
                "Check network connectivity: ping <host>",
                "Check remote service status and performance"
            ]
        ),
        ErrorPattern(
            pattern_id=str(uuid.uuid4()),
            pattern_regex=r"Out of memory|OOM|memory exhausted",
            description="Out of memory error",
            common_causes=[
                "Process consuming too much memory",
                "Memory leak in application",
                "System running low on available memory"
            ],
            suggested_fixes=[
                "Check memory usage: free -h",
                "Check process memory: ps aux | grep <process>",
                "Restart the service to clear memory"
            ]
        ),
        ErrorPattern(
            pattern_id=str(uuid.uuid4()),
            pattern_regex=r"Disk full|No space left|disk space",
            description="Disk space exhausted",
            common_causes=[
                "Disk is full",
                "Log files consuming too much space",
                "Temporary files not being cleaned up"
            ],
            suggested_fixes=[
                "Check disk usage: df -h",
                "Find large files: du -sh /*",
                "Clean up log files: rm -rf /var/log/*.old"
            ]
        ),
        ErrorPattern(
            pattern_id=str(uuid.uuid4()),
            pattern_regex=r"Authentication failed|auth failed|invalid credentials",
            description="Authentication failure",
            common_causes=[
                "Wrong username or password",
                "User account disabled",
                "Authentication service not responding"
            ],
            suggested_fixes=[
                "Verify credentials are correct",
                "Check if user account is active",
                "Verify authentication service is running"
            ]
        ),
        ErrorPattern(
            pattern_id=str(uuid.uuid4()),
            pattern_regex=r"Database error|database connection|SQL error",
            description="Database operation error",
            common_causes=[
                "Database server not running",
                "Database connection string incorrect",
                "Database credentials invalid"
            ],
            suggested_fixes=[
                "Check if database server is running",
                "Verify database connection string",
                "Check database user credentials"
            ]
        ),
    ]
    
    for pattern in error_patterns:
        try:
            db.insert_error_pattern(pattern)
            print(f"✓ Seeded error pattern: {pattern.description}")
        except Exception as e:
            print(f"✗ Failed to seed error pattern {pattern.description}: {e}")
    
    print(f"✓ Seeded {len(error_patterns)} error patterns")


def create_default_admin_user():
    """Create default admin user if it doesn't exist."""
    print("\nCreating default admin user...")
    
    try:
        existing_user = get_user(DEFAULT_ADMIN_EMAIL)
        if existing_user:
            print(f"✓ Admin user already exists: {DEFAULT_ADMIN_EMAIL}")
            return
        
        user = create_user(
            email=DEFAULT_ADMIN_EMAIL,
            password=DEFAULT_ADMIN_PASSWORD,
            role="ADMIN"
        )
        print(f"✓ Created default admin user: {DEFAULT_ADMIN_EMAIL}")
        print(f"  WARNING: Change the default password immediately in production!")
        print(f"  Default password: {DEFAULT_ADMIN_PASSWORD}")
        
    except IntegrityError as e:
        print(f"✓ Admin user already exists: {e}")
    except Exception as e:
        print(f"✗ Failed to create admin user: {e}")
        raise


def register_sample_scripts():
    """Register sample infrastructure scripts in the Script Registry."""
    print("\nRegistering sample scripts...")
    
    sample_scripts = [
        Script(
            script_id="check_cpu",
            name="Check CPU Usage",
            file_path="scripts/check_cpu.py",
            language=ScriptLanguage.PYTHON,
            mapped_intents=[Intent.QUERY_METRICS],
            parameters=[],
            is_read_only=True,
            registered_by=DEFAULT_ADMIN_EMAIL,
            created_at=datetime.now(timezone.utc)
        ),
        Script(
            script_id="check_memory",
            name="Check Memory Usage",
            file_path="scripts/check_memory.py",
            language=ScriptLanguage.PYTHON,
            mapped_intents=[Intent.QUERY_METRICS],
            parameters=[],
            is_read_only=True,
            registered_by=DEFAULT_ADMIN_EMAIL,
            created_at=datetime.now(timezone.utc)
        ),
        Script(
            script_id="check_disk",
            name="Check Disk Space",
            file_path="scripts/check_disk.py",
            language=ScriptLanguage.PYTHON,
            mapped_intents=[Intent.QUERY_METRICS],
            parameters=[],
            is_read_only=True,
            registered_by=DEFAULT_ADMIN_EMAIL,
            created_at=datetime.now(timezone.utc)
        ),
        Script(
            script_id="check_service",
            name="Check Service Status",
            file_path="scripts/check_service.sh",
            language=ScriptLanguage.BASH,
            mapped_intents=[Intent.CHECK_STATUS],
            parameters=[
                Parameter(
                    name="service_name",
                    type="string",
                    required=True,
                    description="Name of the service to check"
                )
            ],
            is_read_only=True,
            registered_by=DEFAULT_ADMIN_EMAIL,
            created_at=datetime.now(timezone.utc)
        ),
        Script(
            script_id="restart_service",
            name="Restart Service",
            file_path="scripts/restart_service.sh",
            language=ScriptLanguage.BASH,
            mapped_intents=[Intent.RESTART_SERVICE],
            parameters=[
                Parameter(
                    name="service_name",
                    type="string",
                    required=True,
                    description="Name of the service to restart"
                )
            ],
            is_read_only=False,
            registered_by=DEFAULT_ADMIN_EMAIL,
            created_at=datetime.now(timezone.utc)
        ),
    ]
    
    for script in sample_scripts:
        try:
            success = db.insert_script(script)
            if success:
                print(f"✓ Registered script: {script.name} ({script.script_id})")
            else:
                print(f"⊘ Script already registered: {script.name} ({script.script_id})")
        except Exception as e:
            print(f"✗ Failed to register script {script.name}: {e}")
    
    print(f"✓ Registered {len(sample_scripts)} sample scripts")


def main():
    """Run all initialization steps."""
    print("=" * 60)
    print("Nexus Intelligent Chatbot System - Database Initialization")
    print("=" * 60)
    
    try:
        initialize_database()
        seed_error_patterns()
        create_default_admin_user()
        register_sample_scripts()
        
        print("\n" + "=" * 60)
        print("✓ Database initialization completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Change the default admin password in production")
        print("2. Start the Nexus API server")
        print("3. Test the system with sample commands")
        
        return 0
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"✗ Database initialization failed: {e}")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
