from datetime import timedelta
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from models import UserCreate, UserLogin, User, Token, TokenData
from auth import (
    hash_password, 
    verify_password, 
    create_access_token, 
    get_current_user
)
from database import get_user, create_user, user_exists
from config import get_settings

app = FastAPI(title="Nexus Auth API", version="1.0.0")
settings = get_settings()

@app.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate):
    """Register a new user"""
    if user_exists(user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    try:
        created_user = create_user(user.email, user.password)
        return User(email=created_user["email"], is_active=created_user["is_active"])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/login", response_model=Token)
async def login(user: UserLogin):
    """Login with email and password"""
    db_user = get_user(user.email)
    
    if not db_user or not verify_password(user.password, db_user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, 
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """OAuth2 compatible token endpoint"""
    db_user = get_user(form_data.username)  # OAuth2 uses 'username' field
    
    if not db_user or not verify_password(form_data.password, db_user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user["email"]}, 
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me", response_model=User)
async def get_me(current_user: TokenData = Depends(get_current_user)):
    """Get current user info"""
    db_user = get_user(current_user.email)
    
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return User(email=db_user["email"], is_active=db_user["is_active"])

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Nexus Auth API is running",
        "endpoints": {
            "register": "POST /register",
            "login": "POST /login",
            "token": "POST /token",
            "me": "GET /me (requires auth)"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
