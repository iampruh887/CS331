"""
Property-based tests for configuration management.

Feature: nexus-complete-system
Tests for Properties 50-53 related to configuration management.
"""

import pytest
from hypothesis import given, settings, strategies as st, HealthCheck
import os
from unittest.mock import patch
from nexus.config import Config, ConfigurationError


# Strategies for generating test data
@st.composite
def valid_jwt_secrets(draw):
    """Generate valid JWT secrets (at least 32 characters)"""
    return draw(st.text(
        alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*',
        min_size=32,
        max_size=64
    ))


@st.composite
def valid_api_keys(draw):
    """Generate valid API keys"""
    return draw(st.text(
        alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-',
        min_size=10,
        max_size=50
    ))


@st.composite
def valid_database_urls(draw):
    """Generate valid database URLs"""
    db_type = draw(st.sampled_from(['sqlite', 'postgresql']))
    if db_type == 'sqlite':
        path = draw(st.text(
            alphabet='abcdefghijklmnopqrstuvwxyz0123456789_-',
            min_size=1,
            max_size=20
        ))
        return f"sqlite:///./{path}.db"
    else:
        host = draw(st.text(
            alphabet='abcdefghijklmnopqrstuvwxyz0123456789',
            min_size=1,
            max_size=10
        ))
        return f"postgresql://user:pass@{host}:5432/nexus"


@st.composite
def valid_confidence_thresholds(draw):
    """Generate valid confidence thresholds (0.0 to 1.0)"""
    return draw(st.floats(min_value=0.0, max_value=1.0))


@st.composite
def valid_positive_integers(draw):
    """Generate valid positive integers"""
    return draw(st.integers(min_value=1, max_value=1000))


@st.composite
def valid_positive_floats(draw):
    """Generate valid positive floats"""
    return draw(st.floats(min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False))


# Property 50: Configuration loading
@settings(max_examples=50, deadline=None)
@given(
    jwt_secret=valid_jwt_secrets(),
    gemini_key=valid_api_keys(),
    database_url=valid_database_urls()
)
def test_property_50_configuration_loading(jwt_secret, gemini_key, database_url):
    """
    Feature: nexus-complete-system, Property 50: Configuration loading
    
    For any required configuration parameter (JWT_SECRET, DATABASE_URL, etc.), 
    the system should successfully load it from environment variables at startup.
    
    Validates: Requirements 15.1
    """
    with patch.dict(os.environ, {
        'JWT_SECRET': jwt_secret,
        'GEMINI_API_KEY': gemini_key,
        'DATABASE_URL': database_url
    }, clear=True):
        # Should not raise ConfigurationError
        config = Config()
        
        # Verify all required parameters are loaded
        assert config.JWT_SECRET == jwt_secret
        assert config.GEMINI_API_KEY == gemini_key
        assert config.DATABASE_URL == database_url


# Property 51: Configuration parameter support
@settings(max_examples=50, deadline=None)
@given(
    jwt_secret=valid_jwt_secrets(),
    gemini_key=valid_api_keys(),
    database_url=valid_database_urls(),
    token_expiry=valid_positive_integers(),
    confidence_threshold=valid_confidence_thresholds(),
    max_concurrent_tasks=valid_positive_integers(),
    calendar_key=valid_api_keys()
)
def test_property_51_configuration_parameter_support(
    jwt_secret, gemini_key, database_url, token_expiry,
    confidence_threshold, max_concurrent_tasks, calendar_key
):
    """
    Feature: nexus-complete-system, Property 51: Configuration parameter support
    
    For any configuration parameter in the set {JWT_SECRET, TOKEN_EXPIRY, DATABASE_URL, 
    CALENDAR_API_KEY, CONFIDENCE_THRESHOLD}, the system should read and use the configured value.
    
    Validates: Requirements 15.2
    """
    with patch.dict(os.environ, {
        'JWT_SECRET': jwt_secret,
        'GEMINI_API_KEY': gemini_key,
        'DATABASE_URL': database_url,
        'TOKEN_EXPIRY_MINUTES': str(token_expiry),
        'CONFIDENCE_THRESHOLD': str(confidence_threshold),
        'MAX_CONCURRENT_TASKS': str(max_concurrent_tasks),
        'CALENDAR_API_KEY': calendar_key
    }, clear=True):
        config = Config()
        
        # Verify all parameters are read and used
        assert config.JWT_SECRET == jwt_secret
        assert config.GEMINI_API_KEY == gemini_key
        assert config.DATABASE_URL == database_url
        assert config.TOKEN_EXPIRY_MINUTES == token_expiry
        assert config.CONFIDENCE_THRESHOLD == confidence_threshold
        assert config.MAX_CONCURRENT_TASKS == max_concurrent_tasks
        assert config.CALENDAR_API_KEY == calendar_key


# Property 52: Invalid configuration rejection
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    jwt_secret=st.text(max_size=31),  # Too short
    gemini_key=valid_api_keys(),
    database_url=valid_database_urls()
)
def test_property_52_invalid_configuration_rejection_short_jwt(jwt_secret, gemini_key, database_url):
    """
    Feature: nexus-complete-system, Property 52: Invalid configuration rejection
    
    For any invalid configuration (missing required parameter, invalid format), 
    the system should fail to start and log a descriptive error message.
    
    Validates: Requirements 15.3
    """
    with patch.dict(os.environ, {
        'JWT_SECRET': jwt_secret,
        'GEMINI_API_KEY': gemini_key,
        'DATABASE_URL': database_url
    }, clear=True):
        # Should raise ConfigurationError for short JWT_SECRET
        with pytest.raises(ConfigurationError) as exc_info:
            Config()
        
        # Error message should be descriptive
        assert "JWT_SECRET" in str(exc_info.value) or "configuration" in str(exc_info.value).lower()


@settings(max_examples=50, deadline=None)
@given(
    jwt_secret=valid_jwt_secrets(),
    database_url=valid_database_urls()
)
def test_property_52_invalid_configuration_rejection_missing_gemini(jwt_secret, database_url):
    """
    Feature: nexus-complete-system, Property 52: Invalid configuration rejection
    
    For any invalid configuration (missing required parameter), 
    the system should fail to start and log a descriptive error message.
    
    Validates: Requirements 15.3
    """
    with patch.dict(os.environ, {
        'JWT_SECRET': jwt_secret,
        'DATABASE_URL': database_url
    }, clear=True):
        # Should raise ConfigurationError for missing GEMINI_API_KEY
        with pytest.raises(ConfigurationError) as exc_info:
            Config()
        
        # Error message should be descriptive
        assert "GEMINI_API_KEY" in str(exc_info.value) or "configuration" in str(exc_info.value).lower()


@settings(max_examples=50, deadline=None)
@given(
    jwt_secret=valid_jwt_secrets(),
    gemini_key=valid_api_keys(),
    invalid_threshold=st.floats(min_value=1.1, max_value=10.0)
)
def test_property_52_invalid_configuration_rejection_invalid_threshold(jwt_secret, gemini_key, invalid_threshold):
    """
    Feature: nexus-complete-system, Property 52: Invalid configuration rejection
    
    For any invalid configuration (invalid format), 
    the system should fail to start and log a descriptive error message.
    
    Validates: Requirements 15.3
    """
    with patch.dict(os.environ, {
        'JWT_SECRET': jwt_secret,
        'GEMINI_API_KEY': gemini_key,
        'DATABASE_URL': 'sqlite:///./test.db',
        'CONFIDENCE_THRESHOLD': str(invalid_threshold)
    }, clear=True):
        # Should raise ConfigurationError for invalid CONFIDENCE_THRESHOLD
        with pytest.raises(ConfigurationError) as exc_info:
            Config()
        
        # Error message should be descriptive
        assert "CONFIDENCE_THRESHOLD" in str(exc_info.value) or "configuration" in str(exc_info.value).lower()


# Property 53: Configuration defaults
@settings(max_examples=50, deadline=None)
@given(
    jwt_secret=valid_jwt_secrets(),
    gemini_key=valid_api_keys()
)
def test_property_53_configuration_defaults(jwt_secret, gemini_key):
    """
    Feature: nexus-complete-system, Property 53: Configuration defaults
    
    For any optional configuration parameter that is not provided, 
    the system should use a documented default value.
    
    Validates: Requirements 15.5
    """
    with patch.dict(os.environ, {
        'JWT_SECRET': jwt_secret,
        'GEMINI_API_KEY': gemini_key
    }, clear=True):
        config = Config()
        
        # Verify defaults are used for optional parameters
        assert config.DATABASE_URL == "sqlite:///./nexus.db"
        assert config.CONFIDENCE_THRESHOLD == 0.5
        assert config.MAX_CONCURRENT_TASKS == 50
        assert config.TOKEN_EXPIRY_MINUTES == 30
        assert config.SCRIPT_EXECUTION_TIMEOUT == 30
        assert config.NLP_PARSING_TIMEOUT == 5
        assert config.CALENDAR_API_TIMEOUT == 10
        assert config.IDENTITY_PROVIDER_TIMEOUT == 5
        assert config.DATABASE_OPERATION_TIMEOUT == 3
        assert config.MAX_RETRIES == 3
        assert config.RETRY_BASE_DELAY == 1.0
        assert config.CONFIRMATION_EXPIRY_MINUTES == 5


# Unit tests for specific examples
def test_config_loads_all_required_parameters():
    """Test that configuration loads all required parameters"""
    with patch.dict(os.environ, {
        'JWT_SECRET': 'a' * 32,
        'GEMINI_API_KEY': 'test_key',
        'DATABASE_URL': 'sqlite:///./test.db'
    }, clear=True):
        config = Config()
        
        assert config.JWT_SECRET == 'a' * 32
        assert config.GEMINI_API_KEY == 'test_key'
        assert config.DATABASE_URL == 'sqlite:///./test.db'


def test_config_uses_default_database_url():
    """Test that DATABASE_URL uses default when not provided"""
    with patch.dict(os.environ, {
        'JWT_SECRET': 'a' * 32,
        'GEMINI_API_KEY': 'test_key'
    }, clear=True):
        config = Config()
        
        assert config.DATABASE_URL == "sqlite:///./nexus.db"


def test_config_uses_default_confidence_threshold():
    """Test that CONFIDENCE_THRESHOLD uses default when not provided"""
    with patch.dict(os.environ, {
        'JWT_SECRET': 'a' * 32,
        'GEMINI_API_KEY': 'test_key'
    }, clear=True):
        config = Config()
        
        assert config.CONFIDENCE_THRESHOLD == 0.5


def test_config_uses_default_max_concurrent_tasks():
    """Test that MAX_CONCURRENT_TASKS uses default when not provided"""
    with patch.dict(os.environ, {
        'JWT_SECRET': 'a' * 32,
        'GEMINI_API_KEY': 'test_key'
    }, clear=True):
        config = Config()
        
        assert config.MAX_CONCURRENT_TASKS == 50


def test_config_rejects_missing_jwt_secret():
    """Test that configuration rejects missing JWT_SECRET"""
    with patch.dict(os.environ, {
        'GEMINI_API_KEY': 'test_key'
    }, clear=True):
        with pytest.raises(ConfigurationError) as exc_info:
            Config()
        
        assert "JWT_SECRET" in str(exc_info.value)


def test_config_rejects_short_jwt_secret():
    """Test that configuration rejects short JWT_SECRET"""
    with patch.dict(os.environ, {
        'JWT_SECRET': 'short',
        'GEMINI_API_KEY': 'test_key'
    }, clear=True):
        with pytest.raises(ConfigurationError) as exc_info:
            Config()
        
        assert "JWT_SECRET" in str(exc_info.value)


def test_config_rejects_missing_gemini_key():
    """Test that configuration rejects missing GEMINI_API_KEY"""
    with patch.dict(os.environ, {
        'JWT_SECRET': 'a' * 32
    }, clear=True):
        with pytest.raises(ConfigurationError) as exc_info:
            Config()
        
        assert "GEMINI_API_KEY" in str(exc_info.value)


def test_config_rejects_invalid_confidence_threshold():
    """Test that configuration rejects invalid CONFIDENCE_THRESHOLD"""
    with patch.dict(os.environ, {
        'JWT_SECRET': 'a' * 32,
        'GEMINI_API_KEY': 'test_key',
        'CONFIDENCE_THRESHOLD': '1.5'
    }, clear=True):
        with pytest.raises(ConfigurationError) as exc_info:
            Config()
        
        assert "CONFIDENCE_THRESHOLD" in str(exc_info.value)


def test_config_rejects_negative_confidence_threshold():
    """Test that configuration rejects negative CONFIDENCE_THRESHOLD"""
    with patch.dict(os.environ, {
        'JWT_SECRET': 'a' * 32,
        'GEMINI_API_KEY': 'test_key',
        'CONFIDENCE_THRESHOLD': '-0.1'
    }, clear=True):
        with pytest.raises(ConfigurationError) as exc_info:
            Config()
        
        assert "CONFIDENCE_THRESHOLD" in str(exc_info.value)


def test_config_rejects_zero_max_concurrent_tasks():
    """Test that configuration rejects zero MAX_CONCURRENT_TASKS"""
    with patch.dict(os.environ, {
        'JWT_SECRET': 'a' * 32,
        'GEMINI_API_KEY': 'test_key',
        'MAX_CONCURRENT_TASKS': '0'
    }, clear=True):
        with pytest.raises(ConfigurationError) as exc_info:
            Config()
        
        assert "MAX_CONCURRENT_TASKS" in str(exc_info.value)


def test_config_accepts_custom_values():
    """Test that configuration accepts custom values"""
    with patch.dict(os.environ, {
        'JWT_SECRET': 'a' * 32,
        'GEMINI_API_KEY': 'test_key',
        'CONFIDENCE_THRESHOLD': '0.7',
        'MAX_CONCURRENT_TASKS': '100',
        'TOKEN_EXPIRY_MINUTES': '60'
    }, clear=True):
        config = Config()
        
        assert config.CONFIDENCE_THRESHOLD == 0.7
        assert config.MAX_CONCURRENT_TASKS == 100
        assert config.TOKEN_EXPIRY_MINUTES == 60


def test_config_get_database_path():
    """Test that get_database_path extracts path correctly"""
    with patch.dict(os.environ, {
        'JWT_SECRET': 'a' * 32,
        'GEMINI_API_KEY': 'test_key',
        'DATABASE_URL': 'sqlite:///./nexus_test.db'
    }, clear=True):
        config = Config()
        
        path = config.get_database_path()
        assert path == './nexus_test.db'


def test_config_repr_masks_sensitive_data():
    """Test that config representation masks sensitive data"""
    with patch.dict(os.environ, {
        'JWT_SECRET': 'a' * 32,
        'GEMINI_API_KEY': 'test_key'
    }, clear=True):
        config = Config()
        
        repr_str = repr(config)
        assert '***MASKED***' in repr_str
        assert 'a' * 32 not in repr_str
        assert 'test_key' not in repr_str


def test_config_optional_calendar_key():
    """Test that CALENDAR_API_KEY is optional"""
    with patch.dict(os.environ, {
        'JWT_SECRET': 'a' * 32,
        'GEMINI_API_KEY': 'test_key'
    }, clear=True):
        config = Config()
        
        # Should be None when not provided
        assert config.CALENDAR_API_KEY is None


def test_config_with_calendar_key():
    """Test that CALENDAR_API_KEY is used when provided"""
    with patch.dict(os.environ, {
        'JWT_SECRET': 'a' * 32,
        'GEMINI_API_KEY': 'test_key',
        'CALENDAR_API_KEY': 'calendar_key_123'
    }, clear=True):
        config = Config()
        
        assert config.CALENDAR_API_KEY == 'calendar_key_123'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
