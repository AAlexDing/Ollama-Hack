from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from src.config import get_config

config = get_config()


def hash_password(password: str) -> str:
    """
    Hash the given password using bcrypt.
    
    Note: bcrypt has a maximum password length of 72 bytes.
    If the password exceeds this limit, it will be truncated.
    """
    # bcrypt has a maximum password length of 72 bytes
    # Encode to bytes to check length, then truncate if necessary
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    # Generate salt and hash password
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against the given hash.
    
    Note: bcrypt has a maximum password length of 72 bytes.
    If the password exceeds this limit, it will be truncated to match the hash.
    """
    # bcrypt has a maximum password length of 72 bytes
    # Encode to bytes to check length, then truncate if necessary
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    # Verify password
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=config.app.access_token_expire_minutes
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.app.secret_key, algorithm=config.app.algorithm)
    return encoded_jwt
