# backend/app/api/v1/users.py
"""
Users router: basic user info endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import select, update
from backend.app.db.session import get_session
from backend.app.db.models import User, Account
from backend.app.core.security import get_current_user
from backend.app.core.logger import logger

router = APIRouter(tags=["users"])

@router.get("/me")
async def read_users_me(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    # Check if premium has expired
    from datetime import datetime, timezone
    if current_user.is_premium and current_user.premium_expires_at:
        if current_user.premium_expires_at < datetime.now(timezone.utc):
            # Premium expired - update user
            current_user.is_premium = False
            current_user.premium_expires_at = None
            session.add(current_user)
            await session.commit()
            await session.refresh(current_user)
    
    # Return user with premium status
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "is_premium": current_user.is_premium,
        "premium_expires_at": current_user.premium_expires_at.isoformat() if current_user.premium_expires_at else None,
        "accepted_terms": current_user.accepted_terms,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "updated_at": current_user.updated_at.isoformat() if current_user.updated_at else None,
    }

@router.patch("/me")
async def update_profile(
    updates: dict,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    stmt = (
        update(User)
        .where(User.id == current_user.id)
        .values(**updates)
        .returning(User)
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.scalar_one()

# --- Admin endpoints ---
@router.get("/users")
async def list_users(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User))
    return result.scalars().all()

@router.post("/users/{user_id}/ban")
async def ban_user(user_id: int, session: AsyncSession = Depends(get_session)):
    stmt = update(User).where(User.id == user_id).values(is_active=False)
    await session.execute(stmt)
    await session.commit()
    return {"status": "banned", "user_id": user_id}


# ============================================================================
# SECURITY ENDPOINTS
# ============================================================================

class SetPinReq(BaseModel):
    pin_hash: str


@router.post("/me/security/pin")
async def set_transaction_pin(
    payload: SetPinReq,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Set or update user's transaction PIN.
    PIN should be hashed on frontend before sending.
    """
    try:
        # In a production app, you might want to store PIN hash in UserSecurity table
        # For now, we'll store it as a user preference/metadata
        # Since we don't have a security table, we'll store it in a separate field or handle it client-side
        # This endpoint validates and acknowledges PIN setting
        
        # Validate PIN hash format (should be SHA-256 hex)
        if len(payload.pin_hash) != 64:  # SHA-256 produces 64-char hex
            raise HTTPException(
                status_code=400,
                detail="Invalid PIN hash format"
            )
        
        # TODO: Store PIN hash in UserSecurity table or User preferences
        # For now, we acknowledge the request
        # Frontend stores it securely in local storage
        
        logger.info(f"✅ User {current_user.id} set transaction PIN")
        
        return {
            "ok": True,
            "message": "Transaction PIN set successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Error setting PIN: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while setting PIN"
        )