"""
Configuration management for the Nexus Intelligent Chatbot System.

Loads configuration from environment variables with validation and default values.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing required parameters."""
    pass


class Config:
    """
    Configuration manager for Nexus system.
    
    Loads and validates all configuration parameters from environment variables.
    Provides default values for optional parameters.
    """
    
    # Authentication
    JWT_SECRET: str
    TOKEN_EXPIRY_MINUTES: int
    
    # Database
    DATABASE_URL: str
    
    # External APIs
    GEMINI_API_KEY: str
    CALENDAR_API_KEY: Optional[str]
    
    # NLP Configuration
    CONFIDENCE_THRESHOLD: float
    
    # Task Execution
    MAX_CONCURRENT_TASKS: int
    SCRIPT_EXECUTION_TIMEOUT: int
    
    # Timeouts (in seconds)
    NLP_PARSING_TIMEOUT: int
    CALENDAR_API_TIMEOUT: int
    IDENTITY_PROVIDER_TIMEOUT: int
    DATABASE_OPERATION_TIMEOUT: int
    
    # Retry Configuration
    MAX_RETRIES: int
    RETRY_BASE_DELAY: float
    
    # Confirmation
    CONFIRMATION_EXPIRY_MINUTES: int
    
    def __init__(self):
        """Initialize configuration by loading and validating environment variables."""
        self._load_configuration()
        self._validate_configuration()
    
    def _load_configuration(self):
        """Load configuration from environment variables."""
        # Required parameters
        self.JWT_SECRET = os.getenv("JWT_SECRET", "")
        self.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./nexus.db")
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
        
        # Optional parameters with defaults
        self.TOKEN_EXPIRY_MINUTES = int(os.getenv("TOKEN_EXPIRY_MINUTES", "30"))
        self.CALENDAR_API_KEY = os.getenv("CALENDAR_API_KEY")
        self.CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.5"))
        self.MAX_CONCURRENT_TASKS = int(os.getenv("MAX_CONCURRENT_TASKS", "50"))
        self.SCRIPT_EXECUTION_TIMEOUT = int(os.getenv("SCRIPT_EXECUTION_TIMEOUT", "30"))
        
        # Timeouts
        self.NLP_PARSING_TIMEOUT = int(os.getenv("NLP_PARSING_TIMEOUT", "5"))
        self.CALENDAR_API_TIMEOUT = int(os.getenv("CALENDAR_API_TIMEOUT", "10"))
        self.IDENTITY_PROVIDER_TIMEOUT = int(os.getenv("IDENTITY_PROVIDER_TIMEOUT", "5"))
        self.DATABASE_OPERATION_TIMEOUT = int(os.getenv("DATABASE_OPERATION_TIMEOUT", "3"))
        
        # Retry configuration
        self.MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
        self.RETRY_BASE_DELAY = float(os.getenv("RETRY_BASE_DELAY", "1.0"))
        
        # Confirmation
        self.CONFIRMATION_EXPIRY_MINUTES = int(os.getenv("CONFIRMATION_EXPIRY_MINUTES", "5"))
    
    def _validate_configuration(self):
        """Validate required configuration parameters."""
        errors = []
        
        # Validate JWT_SECRET
        if not self.JWT_SECRET:
            errors.append("JWT_SECRET is required")
        elif len(self.JWT_SECRET) < 32:
            errors.append("JWT_SECRET must be at least 32 characters")
        
        # Validate GEMINI_API_KEY
        if not self.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY is required")
        
        # Validate DATABASE_URL
        if not self.DATABASE_URL:
            errors.append("DATABASE_URL is required")
        
        # Validate numeric ranges
        if self.CONFIDENCE_THRESHOLD < 0 or self.CONFIDENCE_THRESHOLD > 1:
            errors.append("CONFIDENCE_THRESHOLD must be between 0 and 1")
        
        if self.MAX_CONCURRENT_TASKS < 1:
            errors.append("MAX_CONCURRENT_TASKS must be at least 1")
        
        if self.TOKEN_EXPIRY_MINUTES < 1:
            errors.append("TOKEN_EXPIRY_MINUTES must be at least 1")
        
        if self.SCRIPT_EXECUTION_TIMEOUT < 1:
            errors.append("SCRIPT_EXECUTION_TIMEOUT must be at least 1")
        
        if errors:
            error_message = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ConfigurationError(error_message)
    
    def get_database_path(self) -> str:
        """Extract database file path from DATABASE_URL."""
        if self.DATABASE_URL.startswith("sqlite:///"):
            return self.DATABASE_URL.replace("sqlite:///", "")
        return self.DATABASE_URL
    
    def __repr__(self) -> str:
        """String representation (masks sensitive values)."""
        return (
            f"Config("
            f"JWT_SECRET=***MASKED***, "
            f"DATABASE_URL={self.DATABASE_URL}, "
            f"GEMINI_API_KEY=***MASKED***, "
            f"CONFIDENCE_THRESHOLD={self.CONFIDENCE_THRESHOLD}, "
            f"MAX_CONCURRENT_TASKS={self.MAX_CONCURRENT_TASKS}"
            f")"
        )


# Global configuration instance
config = Config()
