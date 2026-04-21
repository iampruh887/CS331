"""
Error handling and resilience utilities for the Nexus Intelligent Chatbot System.

This module provides decorators and utilities for:
- Retry logic with exponential backoff for transient failures
- Timeout handling for external API calls
- Exception logging with stack traces
- Input validation before processing
"""

import asyncio
import functools
import logging
import re
import time
from typing import Any, Callable, Optional, TypeVar, Union
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Type variables for decorators
F = TypeVar('F', bound=Callable[..., Any])
AsyncF = TypeVar('AsyncF', bound=Callable[..., Any])


class RetryError(Exception):
    """Raised when all retry attempts are exhausted."""
    pass


class TimeoutError(Exception):
    """Raised when an operation exceeds the timeout."""
    pass


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (Exception,)
) -> Callable[[F], F]:
    """
    Decorator for retry logic with exponential backoff.
    
    Retries a function on failure with exponentially increasing delays.
    Useful for handling transient failures like network timeouts.
    
    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        exponential_base: Base for exponential backoff (default: 2.0)
        jitter: Add random jitter to delays (default: True)
        retryable_exceptions: Tuple of exceptions to retry on (default: all)
    
    Returns:
        Decorated function that retries on failure
    
    Raises:
        RetryError: When all retry attempts are exhausted
    
    Example:
        @retry(max_attempts=3, base_delay=1.0)
        def call_external_api():
            return requests.get("https://api.example.com")
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts - 1:
                        # Calculate delay with exponential backoff
                        delay = base_delay * (exponential_base ** attempt)
                        
                        # Add jitter if enabled
                        if jitter:
                            import random
                            delay = delay * (0.5 + random.random())
                        
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {str(e)}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {str(e)}"
                        )
            
            raise RetryError(
                f"Failed after {max_attempts} attempts: {str(last_exception)}"
            ) from last_exception
        
        return wrapper  # type: ignore
    
    return decorator


def async_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (Exception,)
) -> Callable[[AsyncF], AsyncF]:
    """
    Async version of retry decorator with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        exponential_base: Base for exponential backoff (default: 2.0)
        jitter: Add random jitter to delays (default: True)
        retryable_exceptions: Tuple of exceptions to retry on (default: all)
    
    Returns:
        Decorated async function that retries on failure
    
    Raises:
        RetryError: When all retry attempts are exhausted
    """
    def decorator(func: AsyncF) -> AsyncF:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts - 1:
                        # Calculate delay with exponential backoff
                        delay = base_delay * (exponential_base ** attempt)
                        
                        # Add jitter if enabled
                        if jitter:
                            import random
                            delay = delay * (0.5 + random.random())
                        
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {str(e)}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {str(e)}"
                        )
            
            raise RetryError(
                f"Failed after {max_attempts} attempts: {str(last_exception)}"
            ) from last_exception
        
        return wrapper  # type: ignore
    
    return decorator


def timeout(seconds: float) -> Callable[[F], F]:
    """
    Decorator for timeout handling on synchronous functions.
    
    Raises TimeoutError if the function doesn't complete within the specified time.
    Note: This uses signal-based timeout which only works on Unix systems.
    
    Args:
        seconds: Timeout duration in seconds
    
    Returns:
        Decorated function with timeout
    
    Raises:
        TimeoutError: When function exceeds timeout
    
    Example:
        @timeout(5.0)
        def slow_operation():
            time.sleep(10)
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            import signal
            
            def timeout_handler(signum: int, frame: Any) -> None:
                raise TimeoutError(
                    f"Function {func.__name__} exceeded timeout of {seconds}s"
                )
            
            # Set the signal handler and alarm
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(seconds) + 1)  # Round up to ensure we catch it
            
            try:
                result = func(*args, **kwargs)
            finally:
                # Disable the alarm
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
            
            return result
        
        return wrapper  # type: ignore
    
    return decorator


def async_timeout(seconds: float) -> Callable[[AsyncF], AsyncF]:
    """
    Decorator for timeout handling on async functions.
    
    Args:
        seconds: Timeout duration in seconds
    
    Returns:
        Decorated async function with timeout
    
    Raises:
        TimeoutError: When function exceeds timeout
    
    Example:
        @async_timeout(5.0)
        async def slow_api_call():
            await asyncio.sleep(10)
    """
    def decorator(func: AsyncF) -> AsyncF:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=seconds
                )
            except asyncio.TimeoutError:
                raise TimeoutError(
                    f"Function {func.__name__} exceeded timeout of {seconds}s"
                )
        
        return wrapper  # type: ignore
    
    return decorator


def log_exception(
    logger_instance: Optional[logging.Logger] = None,
    include_args: bool = False
) -> Callable[[F], F]:
    """
    Decorator for exception logging with stack traces.
    
    Logs exceptions with full stack traces before re-raising them.
    Useful for debugging and monitoring.
    
    Args:
        logger_instance: Logger to use (default: module logger)
        include_args: Include function arguments in log (default: False)
    
    Returns:
        Decorated function with exception logging
    
    Example:
        @log_exception()
        def risky_operation():
            raise ValueError("Something went wrong")
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            log = logger_instance or logger
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Build log message
                msg = f"Exception in {func.__name__}: {type(e).__name__}: {str(e)}"
                
                if include_args:
                    msg += f"\n  Args: {args}\n  Kwargs: {kwargs}"
                
                # Log with stack trace
                log.exception(msg)
                raise
        
        return wrapper  # type: ignore
    
    return decorator


def async_log_exception(
    logger_instance: Optional[logging.Logger] = None,
    include_args: bool = False
) -> Callable[[AsyncF], AsyncF]:
    """
    Async version of log_exception decorator.
    
    Args:
        logger_instance: Logger to use (default: module logger)
        include_args: Include function arguments in log (default: False)
    
    Returns:
        Decorated async function with exception logging
    """
    def decorator(func: AsyncF) -> AsyncF:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            log = logger_instance or logger
            
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Build log message
                msg = f"Exception in {func.__name__}: {type(e).__name__}: {str(e)}"
                
                if include_args:
                    msg += f"\n  Args: {args}\n  Kwargs: {kwargs}"
                
                # Log with stack trace
                log.exception(msg)
                raise
        
        return wrapper  # type: ignore
    
    return decorator


def validate_input(
    validation_func: Callable[[Any], bool],
    error_message: str = "Input validation failed"
) -> Callable[[F], F]:
    """
    Decorator for input validation before processing.
    
    Validates the first argument (typically 'self' or the main input) before
    executing the function.
    
    Args:
        validation_func: Function that returns True if input is valid
        error_message: Error message to raise on validation failure
    
    Returns:
        Decorated function with input validation
    
    Raises:
        ValidationError: When input validation fails
    
    Example:
        def is_valid_email(email):
            return "@" in email
        
        @validate_input(is_valid_email, "Invalid email format")
        def send_email(email):
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Validate first argument (skip 'self' if it's a method)
            if args:
                input_to_validate = args[0]
                if not validation_func(input_to_validate):
                    raise ValidationError(error_message)
            
            return func(*args, **kwargs)
        
        return wrapper  # type: ignore
    
    return decorator


def validate_dict_schema(
    required_keys: Optional[list] = None,
    allowed_keys: Optional[list] = None,
    key_types: Optional[dict] = None
) -> Callable[[F], F]:
    """
    Decorator for validating dictionary input against a schema.
    
    Validates that a dictionary argument contains required keys, only allowed keys,
    and that values match expected types.
    
    Args:
        required_keys: List of keys that must be present
        allowed_keys: List of keys that are allowed (if None, all keys allowed)
        key_types: Dict mapping keys to expected types
    
    Returns:
        Decorated function with schema validation
    
    Raises:
        ValidationError: When schema validation fails
    
    Example:
        @validate_dict_schema(
            required_keys=["name", "email"],
            key_types={"name": str, "email": str}
        )
        def create_user(user_data):
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Find the dictionary argument (typically first arg after self)
            dict_arg = None
            if len(args) > 1:
                dict_arg = args[1]
            elif len(args) == 1 and isinstance(args[0], dict):
                dict_arg = args[0]
            
            if dict_arg and isinstance(dict_arg, dict):
                # Check required keys
                if required_keys:
                    missing = set(required_keys) - set(dict_arg.keys())
                    if missing:
                        raise ValidationError(
                            f"Missing required keys: {', '.join(missing)}"
                        )
                
                # Check allowed keys
                if allowed_keys:
                    extra = set(dict_arg.keys()) - set(allowed_keys)
                    if extra:
                        raise ValidationError(
                            f"Unexpected keys: {', '.join(extra)}"
                        )
                
                # Check key types
                if key_types:
                    for key, expected_type in key_types.items():
                        if key in dict_arg:
                            if not isinstance(dict_arg[key], expected_type):
                                raise ValidationError(
                                    f"Key '{key}' has type {type(dict_arg[key]).__name__}, "
                                    f"expected {expected_type.__name__}"
                                )
            
            return func(*args, **kwargs)
        
        return wrapper  # type: ignore
    
    return decorator


class ExceptionLogger:
    """
    Utility class for logging exceptions with context.
    
    Provides methods for logging exceptions with additional context information
    like user ID, operation name, and custom metadata.
    """
    
    def __init__(self, logger_instance: Optional[logging.Logger] = None):
        """
        Initialize the exception logger.
        
        Args:
            logger_instance: Logger to use (default: module logger)
        """
        self.logger = logger_instance or logger
    
    def log_exception(
        self,
        exception: Exception,
        operation: str,
        user_id: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> None:
        """
        Log an exception with context information.
        
        Args:
            exception: The exception to log
            operation: Name of the operation that failed
            user_id: Optional user ID for context
            metadata: Optional additional metadata
        """
        context_parts = [f"Operation: {operation}"]
        
        if user_id:
            context_parts.append(f"User: {user_id}")
        
        if metadata:
            context_parts.append(f"Metadata: {metadata}")
        
        context = " | ".join(context_parts)
        
        self.logger.exception(
            f"Exception in {operation}: {type(exception).__name__}: {str(exception)} | {context}"
        )
    
    def log_database_error(
        self,
        exception: Exception,
        operation: str,
        query: Optional[str] = None
    ) -> None:
        """
        Log a database error with query information.
        
        Args:
            exception: The database exception
            operation: Name of the database operation
            query: Optional SQL query that failed
        """
        msg = f"Database error in {operation}: {type(exception).__name__}: {str(exception)}"
        
        if query:
            msg += f"\nQuery: {query}"
        
        self.logger.exception(msg)
    
    def log_api_error(
        self,
        exception: Exception,
        api_name: str,
        endpoint: Optional[str] = None,
        status_code: Optional[int] = None
    ) -> None:
        """
        Log an API error with endpoint information.
        
        Args:
            exception: The API exception
            api_name: Name of the API
            endpoint: Optional API endpoint
            status_code: Optional HTTP status code
        """
        msg = f"API error from {api_name}: {type(exception).__name__}: {str(exception)}"
        
        if endpoint:
            msg += f"\nEndpoint: {endpoint}"
        
        if status_code:
            msg += f"\nStatus Code: {status_code}"
        
        self.logger.exception(msg)


def mask_sensitive_data(
    text: str,
    patterns: Optional[dict] = None
) -> str:
    """
    Mask sensitive data in text using regex patterns.
    
    Replaces sensitive information like passwords, API keys, and tokens
    with masked placeholders.
    
    Args:
        text: Text to mask
        patterns: Dict of pattern_name -> regex_pattern (default: common patterns)
    
    Returns:
        Text with sensitive data masked
    
    Example:
        masked = mask_sensitive_data("password=secret123")
        # Returns: "password=***MASKED***"
    """
    if patterns is None:
        patterns = {
            "password": r"password['\"]?\s*[:=]\s*['\"]?([^'\"\\s]+)['\"]?",
            "api_key": r"api[_-]?key['\"]?\s*[:=]\s*['\"]?([^'\"\\s]+)['\"]?",
            "token": r"token['\"]?\s*[:=]\s*['\"]?([^'\"\\s]+)['\"]?",
            "secret": r"secret['\"]?\s*[:=]\s*['\"]?([^'\"\\s]+)['\"]?",
            "authorization": r"authorization['\"]?\s*[:=]\s*['\"]?([^'\"\\s]+)['\"]?",
        }
    
    masked_text = text
    
    for pattern_name, pattern in patterns.items():
        masked_text = re.sub(
            pattern,
            lambda m: m.group(0).replace(m.group(1), "***MASKED***"),
            masked_text,
            flags=re.IGNORECASE
        )
    
    return masked_text


# Global exception logger instance
exception_logger = ExceptionLogger()
