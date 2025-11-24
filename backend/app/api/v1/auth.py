# backend/app/api/v1/auth.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.db.session import get_session
from backend.app.db.models import User, Account, RefreshToken
from backend.app.utils.security import new_refresh_token, hash_refresh_token, REFRESH_TOKEN_EXPIRE_DAYS

# Import from core.security (single source of truth)
from backend.app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user
)

router = APIRouter(tags=["auth"])


class SignupReq(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    currency: str | None = None


class SignupResp(BaseModel):
    id: str
    email: EmailStr
    access_token: str
    refresh_token: str | None = None


class LoginReq(BaseModel):
    email: EmailStr
    password: str


class TokenResp(BaseModel):
    access_token: str
    refresh_token: str | None = None
    user: dict | None = None


@router.post("/signup", response_model=SignupResp, status_code=201)
async def signup(payload: SignupReq, session: AsyncSession = Depends(get_session)):
    """
    Register a new user account.
    Creates user, account, and authentication tokens.
    """
    try:
        # Check if user already exists
        stmt = select(User).where(User.email == payload.email)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            raise HTTPException(status_code=400, detail="User with this email already exists")

        # Create new user
        user = User(
            email=payload.email,
            full_name=payload.full_name,
            password_hash=get_password_hash(payload.password),
            is_active=True,
            accepted_terms=False
        )
        
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        logger.info(f"✅ Created user: {user.id} ({user.email})")

        # Create account with default or provided currency
        account_currency = payload.currency or "GHS"
        account = Account(
            user_id=user.id,
            currency=account_currency,
            available_balance=0.0,
            ledger_balance=0.0
        )
        
        session.add(account)
        await session.commit()
        await session.refresh(account)
        
        logger.info(f"✅ Created account for user {user.id} with currency {account_currency}")

        # Create access token
        access_token = create_access_token({"sub": str(user.id)})
        
        # Create refresh token
        refresh_token_str = new_refresh_token()
        refresh_token_hash = hash_refresh_token(refresh_token_str)
        expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        refresh_token = RefreshToken(
            user_id=user.id,
            token_hash=refresh_token_hash,
            expires_at=expires_at,
            revoked=False
        )
        
        session.add(refresh_token)
        await session.commit()
        
        logger.info(f"✅ Created tokens for user {user.id}")

        return SignupResp(
            id=str(user.id),
            email=user.email,
            access_token=access_token,
            refresh_token=refresh_token_str
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Error during signup: {e}")
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during signup: {str(e)}"
        )


@router.post("/login", response_model=TokenResp)
async def login(payload: LoginReq, session: AsyncSession = Depends(get_session)):
    """
    Authenticate user and return access and refresh tokens.
    """
    try:
        # Find user by email - EXPLICITLY select all columns
        stmt = select(User).where(User.email == payload.email)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"Login attempt for non-existent user: {payload.email}")
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # CRITICAL: Ensure password_hash is loaded before any async operations
        password_hash = user.password_hash
        
        if not password_hash:
            logger.error(f"User {user.id} has no password_hash in database")
            raise HTTPException(status_code=500, detail="Account configuration error")
        
        # Verify password
        if not verify_password(payload.password, password_hash):
            logger.warning(f"Invalid password attempt for user: {payload.email}")
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Check if user is active
        if not getattr(user, 'is_active', True):
            raise HTTPException(status_code=403, detail="Account is inactive")
        
        logger.info(f"✅ User {user.id} logged in successfully")
        
        # Create access token
        access_token = create_access_token({"sub": str(user.id)})
        
        # Create refresh token
        refresh_token_str = new_refresh_token()
        refresh_token_hash = hash_refresh_token(refresh_token_str)
        expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        refresh_token = RefreshToken(
            user_id=user.id,
            token_hash=refresh_token_hash,
            expires_at=expires_at,
            revoked=False
        )
        
        session.add(refresh_token)
        await session.commit()
        
        # Return user data
        user_data = {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "accepted_terms": getattr(user, 'accepted_terms', False)
        }
        
        return TokenResp(
            access_token=access_token,
            refresh_token=refresh_token_str,
            user=user_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Error during login: {e}")
        raise HTTPException(status_code=500, detail="An error occurred during login")


class RefreshReq(BaseModel):
    refresh_token: str


@router.post("/refresh")
async def refresh_token(payload: RefreshReq, session: AsyncSession = Depends(get_session)):
    """
    Refresh access token using a valid refresh token.
    Implements token rotation for security.
    """
    try:
        # Hash the provided refresh token
        hashed = hash_refresh_token(payload.refresh_token)
        
        # Find the refresh token in database
        stmt = select(RefreshToken).where(RefreshToken.token_hash == hashed)
        result = await session.exec(stmt)
        token_record = result.first()
        
        # Validate token exists and is not revoked
        if not token_record:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        # Check if token is revoked
        if getattr(token_record, 'revoked', False):
            raise HTTPException(status_code=401, detail="Refresh token has been revoked")
        
        # Check if token is expired
        expires_at = getattr(token_record, 'expires_at', None)
        if expires_at and expires_at < datetime.utcnow():
            # Update token as revoked if expired
            if hasattr(token_record, 'revoked'):
                token_record.revoked = True
                session.add(token_record)
                await session.commit()
            raise HTTPException(status_code=401, detail="Refresh token expired")
        
        # Revoke old token (rotation)
        if hasattr(token_record, 'revoked'):
            token_record.revoked = True
            session.add(token_record)
        
        # Get user_id safely
        user_id = getattr(token_record, 'user_id', None)
        if not user_id:
            raise HTTPException(status_code=500, detail="Unable to retrieve user ID from token")
        
        # Create new refresh token
        new_refresh_str = new_refresh_token()
        new_hash = hash_refresh_token(new_refresh_str)
        new_expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        new_token_record = RefreshToken(
            user_id=user_id,
            token_hash=new_hash,
            expires_at=new_expires_at,
            revoked=False
        )
        
        session.add(new_token_record)
        await session.commit()
        
        # Create new access token
        access_token = create_access_token({"sub": str(user_id)})
        
        logger.info(f"✅ Refreshed tokens for user {user_id}")
        
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_str
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Error refreshing token: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while refreshing token")


class LogoutReq(BaseModel):
    refresh_token: str


@router.post("/logout")
async def logout(payload: LogoutReq, session: AsyncSession = Depends(get_session)):
    """
    Revoke refresh token to log out user.
    """
    try:
        hashed = hash_refresh_token(payload.refresh_token)
        
        result = await session.exec(
            select(RefreshToken).where(RefreshToken.token_hash == hashed)
        )
        token_record = result.first()
        
        if token_record:
            token_record.revoked = True
            session.add(token_record)
            await session.commit()
            logger.info(f"✅ User {token_record.user_id} logged out")
        
        return {"ok": True, "message": "Logged out successfully"}
        
    except Exception as e:
        logger.exception(f"❌ Error during logout: {e}")
        return {"ok": True, "message": "Logged out"}


class ChangePasswordReq(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordReq,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Change user password. Requires current password verification.
    """
    try:
        # Verify current password
        if not verify_password(payload.current_password, current_user.password_hash):
            raise HTTPException(status_code=401, detail="Current password is incorrect")
        
        # Validate new password (minimum length check)
        if len(payload.new_password) < 8:
            raise HTTPException(
                status_code=400, 
                detail="New password must be at least 8 characters long"
            )
        
        # Hash new password
        new_password_hash = get_password_hash(payload.new_password)
        
        # Update user password
        current_user.password_hash = new_password_hash
        session.add(current_user)
        await session.commit()
        
        logger.info(f"✅ User {current_user.id} changed password")
        
        return {"ok": True, "message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Error changing password: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while changing password"
        )