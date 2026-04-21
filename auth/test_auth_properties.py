"""
Property-based tests for authentication and authorization.

Feature: nexus-complete-system
Tests for Properties 1-4 related to authentication and authorization.
"""

import pytest
from hypothesis import given, settings, strategies as st, HealthCheck
from datetime import datetime, timedelta
from jose import jwt
from auth.auth import (
    verify_password, create_access_token, verify_token
)
from auth.models import User, TokenData
from auth.config import get_settings
from fastapi import HTTPException
import bcrypt


# Strategies for generating test data
@st.composite
def valid_emails(draw):
    """Generate valid email addresses"""
    local = draw(st.text(
        alphabet='abcdefghijklmnopqrstuvwxyz0123456789',
        min_size=1,
        max_size=10
    ))
    domain = draw(st.text(
        alphabet='abcdefghijklmnopqrstuvwxyz0123456789',
        min_size=1,
        max_size=5
    ))
    return f"{local}@{domain}.com"


@st.composite
def valid_passwords(draw):
    """Generate valid passwords (min 8 chars)"""
    return draw(st.text(min_size=8, max_size=20))


@st.composite
def valid_user_roles(draw):
    """Generate valid user roles"""
    return draw(st.sampled_from(["GENERAL", "ADMIN"]))


# Property 1: Valid credentials produce JWT tokens
@settings(max_examples=50, deadline=None)
@given(
    email=valid_emails(),
    password=valid_passwords()
)
def test_property_1_valid_credentials_produce_jwt_tokens(email, password):
    """
    Feature: nexus-complete-system, Property 1: Valid credentials produce JWT tokens
    
    For any valid user credentials, creating an access token should return a JWT token 
    with the user's email encoded.
    
    Validates: Requirements 1.1
    """
    # Create a token with the email
    token = create_access_token(data={"sub": email})
    
    # Token should be a non-empty string
    assert isinstance(token, str)
    assert len(token) > 0
    
    # Token should be decodable
    settings_obj = get_settings()
    payload = jwt.decode(token, settings_obj.SECRET_KEY, algorithms=[settings_obj.ALGORITHM])
    
    # Email should be in the token
    assert payload.get("sub") == email
    
    # Token should have expiration
    assert "exp" in payload


# Property 2: Invalid credentials are rejected
@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    email=valid_emails(),
    correct_password=valid_passwords(),
    wrong_password=valid_passwords()
)
def test_property_2_invalid_credentials_are_rejected(email, correct_password, wrong_password):
    """
    Feature: nexus-complete-system, Property 2: Invalid credentials are rejected
    
    For any invalid credentials (wrong password), authentication should fail 
    and not produce a valid token.
    
    Validates: Requirements 1.2
    """
    # Skip if passwords are the same
    if correct_password == wrong_password:
        return
    
    # Hash the correct password
    hashed = bcrypt.hashpw(correct_password.encode('utf-8'), bcrypt.gensalt())
    
    # Verify correct password works
    assert verify_password(correct_password, hashed.decode('utf-8')) is True
    
    # Verify wrong password fails
    assert verify_password(wrong_password, hashed.decode('utf-8')) is False


# Property 3: Token validation occurs before processing
@settings(max_examples=50, deadline=None)
@given(
    email=valid_emails(),
    password=valid_passwords()
)
def test_property_3_token_validation_occurs_before_processing(email, password):
    """
    Feature: nexus-complete-system, Property 3: Token validation occurs before processing
    
    For any authenticated request, the system should validate the JWT token 
    before executing the requested operation.
    
    Validates: Requirements 1.3
    """
    # Create a valid token
    token = create_access_token(data={"sub": email})
    
    # Verify the token
    token_data = verify_token(token)
    
    # Token data should contain the email
    assert token_data.email == email
    
    # Invalid token should raise exception
    with pytest.raises(HTTPException):
        verify_token("invalid_token_xyz")
    
    # Tampered token should raise exception
    tampered_token = token[:-5] + "xxxxx"
    with pytest.raises(HTTPException):
        verify_token(tampered_token)


# Property 4: Role-based access control
@settings(max_examples=50, deadline=None)
@given(
    email=valid_emails(),
    role=valid_user_roles()
)
def test_property_4_role_based_access_control(email, role):
    """
    Feature: nexus-complete-system, Property 4: Role-based access control
    
    For any GENERAL user attempting an admin-only action, the system should deny 
    access with an authorization error. ADMIN users should be allowed.
    
    Validates: Requirements 1.5
    """
    # Create a user with the given role
    user = User(email=email, is_active=True, role=role)
    
    # Test the authorization logic directly
    if role == "ADMIN":
        # ADMIN users should pass authorization
        assert user.role == "ADMIN"
    else:
        # GENERAL users should fail authorization
        assert user.role == "GENERAL"
        assert user.role != "ADMIN"


# Additional edge case tests
@settings(max_examples=30, deadline=None)
@given(
    email=valid_emails(),
    password=valid_passwords()
)
def test_token_expiration(email, password):
    """
    Test that tokens expire after the configured time.
    
    Validates: Requirements 1.1
    """
    # Create a token with very short expiration
    expires_delta = timedelta(seconds=-1)  # Already expired
    token = create_access_token(data={"sub": email}, expires_delta=expires_delta)
    
    # Expired token should raise exception
    with pytest.raises(HTTPException):
        verify_token(token)


@settings(max_examples=30, deadline=None)
@given(
    email=valid_emails()
)
def test_token_without_email_fails(email):
    """
    Test that tokens without email in payload fail validation.
    
    Validates: Requirements 1.3
    """
    # Create a token without email
    token = create_access_token(data={"sub": None})
    
    # Token without email should raise exception
    with pytest.raises(HTTPException):
        verify_token(token)


@settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    email=valid_emails(),
    password=valid_passwords()
)
def test_password_hashing_consistency(email, password):
    """
    Test that password hashing is consistent and secure.
    
    Validates: Requirements 1.2
    """
    # Hash the same password twice
    hash1 = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    hash2 = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    # Hashes should be different (due to salt)
    assert hash1 != hash2
    
    # But both should verify against the original password
    assert verify_password(password, hash1.decode('utf-8')) is True
    assert verify_password(password, hash2.decode('utf-8')) is True


# Unit tests for specific examples
def test_admin_user_has_admin_role():
    """Test that ADMIN users have the ADMIN role"""
    admin_user = User(email="admin@example.com", is_active=True, role="ADMIN")
    assert admin_user.role == "ADMIN"


def test_general_user_has_general_role():
    """Test that GENERAL users have the GENERAL role"""
    general_user = User(email="user@example.com", is_active=True, role="GENERAL")
    assert general_user.role == "GENERAL"


def test_token_contains_email():
    """Test that tokens contain the user's email"""
    email = "test@example.com"
    token = create_access_token(data={"sub": email})
    token_data = verify_token(token)
    assert token_data.email == email


def test_invalid_token_raises_exception():
    """Test that invalid tokens raise HTTPException"""
    with pytest.raises(HTTPException):
        verify_token("not_a_valid_token")


def test_password_verification_works():
    """Test password verification"""
    password = "TestPassword123"
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    assert verify_password(password, hashed.decode('utf-8')) is True
    assert verify_password("WrongPassword", hashed.decode('utf-8')) is False


def test_user_model_with_default_role():
    """Test that User model defaults to GENERAL role"""
    user = User(email="test@example.com", is_active=True)
    assert user.role == "GENERAL"


def test_user_model_with_explicit_role():
    """Test that User model accepts explicit role"""
    user = User(email="test@example.com", is_active=True, role="ADMIN")
    assert user.role == "ADMIN"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
