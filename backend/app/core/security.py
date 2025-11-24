# backend/app/core/security.py
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import select

# Import settings and logger
from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.db.session import get_session

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = getattr(settings, "ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a bcrypt hash."""
    if not plain_password or not hashed_password:
        return False

    plain_password = str(plain_password).strip().replace("\u0000", "").replace("\n", "").replace("\r", "")
    pw_bytes = plain_password.encode("utf-8", errors="ignore")[:72]

    try:
        # Convert string hash to bytes if needed
        if isinstance(hashed_password, str):
            hashed_password = hashed_password.encode('utf-8')
        return bcrypt.checkpw(pw_bytes, hashed_password)
    except Exception as e:
        logger.warning(f"Password verification error: {e}")
        return False



def get_password_hash(password: str) -> str:
    """
    Fully safe password hasher for bcrypt — always strips, cleans, and truncates
    to 72 bytes maximum before hashing, so bcrypt never throws errors.
    """
    if not password:
        raise ValueError("password is required")

    # Remove any accidental whitespace, unicode padding, or nulls
    password = str(password).strip().replace("\u0000", "").replace("\n", "").replace("\r", "")

    # Encode and truncate to exactly 72 bytes max
    pw_bytes = password.encode("utf-8", errors="ignore")[:72]

    try:
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(pw_bytes, salt)
        return hashed.decode('utf-8')
    except Exception as e:
        logger.exception(f"Password hash failed: {e}")
        # Fallback: ensure truncation again before hashing
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password[:72].encode("utf-8"), salt)
        return hashed.decode('utf-8')




def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    
    # Ensure 'sub' field exists (user identifier)
    if "sub" not in to_encode:
        if "username" in to_encode:
            to_encode["sub"] = to_encode["username"]
        elif "user_id" in to_encode:
            to_encode["sub"] = str(to_encode["user_id"])
    
    # Always convert sub to string for consistency
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session)
):
    """
    Validate JWT token and return the authenticated user.
    This function requires a database session to be injected.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: Optional[str] = payload.get("sub")
        
        if user_id is None:
            logger.warning("Token missing 'sub' claim")
            raise credentials_exception
        
        # Import User model here to avoid circular imports
        from backend.app.db.models import User
        
        # Fetch user from database - use session.execute for reliable model retrieval
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"User {user_id} not found in database")
            raise credentials_exception
        
        # Check if user is active
        if not getattr(user, 'is_active', True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return user
        
    except HTTPException as e:
        # Re-raise HTTP exceptions (401, 403) as-is
        raise
    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise credentials_exception
    except Exception as e:
        logger.exception(f"Error in get_current_user: {e}")
        raise credentials_exception