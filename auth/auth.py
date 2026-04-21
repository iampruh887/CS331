from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from auth.config import get_settings
from auth.models import TokenData, User
from auth.database import get_user

settings = get_settings()

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its bcrypt hash."""
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> TokenData:
    """Verify and decode JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        return TokenData(email=email)
    except JWTError:
        raise credentials_exception

async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    """Get current user from token"""
    return verify_token(token)

async def get_current_user_with_role(token: str = Depends(oauth2_scheme)) -> User:
    """
    Get current user with role information from token.
    
    This dependency retrieves the authenticated user's full profile including their role.
    
    Args:
        token: JWT token from the Authorization header
        
    Returns:
        User object with email, is_active, and role
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    token_data = verify_token(token)
    
    db_user = get_user(token_data.email)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return User(
        email=db_user["email"],
        is_active=db_user["is_active"],
        role=db_user.get("role", "GENERAL")
    )

async def require_admin(current_user: User = Depends(get_current_user_with_role)) -> User:
    """
    Dependency to enforce admin-only access.
    
    Use this as a dependency in FastAPI endpoints that should only be accessible to ADMIN users.
    
    Example:
        @app.post("/admin/scripts")
        async def register_script(admin_user: User = Depends(require_admin)):
            # Only ADMIN users can access this endpoint
            pass
    
    Args:
        current_user: Current authenticated user with role
        
    Returns:
        User object if user is ADMIN
        
    Raises:
        HTTPException: If user is not ADMIN
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user
