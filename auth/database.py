"""Database operations using SQLite for user management"""
import sqlite3
from typing import Dict, Optional
import bcrypt
from auth.config import get_settings

settings = get_settings()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

# Extract database file path from SQLite URL
DB_PATH = settings.DATABASE_URL.replace("sqlite:///./", "")


def init_db():
    """Initialize the database with the users table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create users table if it doesn't exist
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
    
    conn.commit()
    conn.close()


def create_user(email: str, password: str, role: str = "GENERAL") -> Dict:
    """
    Create a new user in the database
    
    Args:
        email: User's email address
        password: User's plain text password (will be hashed)
        role: User's role (GENERAL or ADMIN)
    
    Returns:
        Dictionary containing user data
    
    Raises:
        sqlite3.IntegrityError: If email already exists
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    hashed_password = hash_password(password)
    
    try:
        cursor.execute("""
            INSERT INTO users (email, hashed_password, role)
            VALUES (?, ?, ?)
        """, (email, hashed_password, role))
        
        conn.commit()
        user_id = cursor.lastrowid
        
        # Fetch the created user
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        return {
            "id": user[0],
            "email": user[1],
            "hashed_password": user[2],
            "is_active": user[3],
            "role": user[4],
            "created_at": user[5],
            "updated_at": user[6]
        }
    except sqlite3.IntegrityError as e:
        conn.close()
        raise IntegrityError(f"Email {email} is already registered") from e


class IntegrityError(Exception):
    """Custom exception for database integrity errors"""
    pass


def get_user(email: str) -> Optional[Dict]:
    """
    Retrieve a user by email from the database
    
    Args:
        email: User's email address
    
    Returns:
        Dictionary containing user data, or None if not found
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {
            "id": user[0],
            "email": user[1],
            "hashed_password": user[2],
            "is_active": user[3],
            "role": user[4],
            "created_at": user[5],
            "updated_at": user[6]
        }
    
    return None


def user_exists(email: str) -> bool:
    """
    Check if a user exists in the database
    
    Args:
        email: User's email address
    
    Returns:
        True if user exists, False otherwise
    """
    return get_user(email) is not None


def delete_user(email: str) -> bool:
    """
    Delete a user from the database
    
    Args:
        email: User's email address
    
    Returns:
        True if user was deleted, False if user not found
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM users WHERE email = ?", (email,))
    conn.commit()
    
    deleted = cursor.rowcount > 0
    conn.close()
    
    return deleted


def get_all_users() -> list:
    """
    Retrieve all users from the database
    
    Returns:
        List of dictionaries containing user data
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    conn.close()
    
    return [
        {
            "id": user[0],
            "email": user[1],
            "hashed_password": user[2],
            "is_active": user[3],
            "role": user[4],
            "created_at": user[5],
            "updated_at": user[6]
        }
        for user in users
    ]


def update_user_role(email: str, role: str) -> Optional[Dict]:
    """
    Update a user's role
    
    Args:
        email: User's email address
        role: New role (GENERAL or ADMIN)
    
    Returns:
        Updated user dictionary, or None if not found
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE users 
        SET role = ?, updated_at = CURRENT_TIMESTAMP 
        WHERE email = ?
    """, (role, email))
    
    conn.commit()
    
    # Fetch updated user
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {
            "id": user[0],
            "email": user[1],
            "hashed_password": user[2],
            "is_active": user[3],
            "role": user[4],
            "created_at": user[5],
            "updated_at": user[6]
        }
    
    return None


# Initialize database on import
init_db()
