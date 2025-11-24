"""
AI API endpoints for VyRaTrader.
Handles Prince AI chat, signal generation, and daily limits.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import func, and_
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.app.db.session import get_session
from backend.app.db.models import User, PrinceSignalAlert
from backend.app.core.security import get_current_user
from backend.app.core.logger import logger
from backend.app.services.ai_service import AIService as AIServiceWrapper
from backend.app.services.prince_ai_enhanced import prince_ai

router = APIRouter(tags=["AI"])

# Initialize AI service
ai_service = AIServiceWrapper()

# Per-market signal limits configuration
MARKET_BASE_LIMITS = {
    "crypto": 2,
    "forex": 2,
}

MARKET_MAX_LIMITS = {
    "crypto": 4,
    "forex": 4,
}

# Premium user limits - reasonable amount per market
PREMIUM_MARKET_LIMITS = {
    "crypto": 5,
    "forex": 5,
}

# Quality thresholds
HIGH_QUALITY_THRESHOLD = {
    "confidence_min": 0.75,
    "risk_reward_min": 2.5,
    "strategies_agreement": 6,
}

EXCEPTIONAL_QUALITY_THRESHOLD = {
    "confidence_min": 0.85,
    "risk_reward_min": 3.0,
    "strategies_agreement": 7,
}

# Map frontend categories to backend market names
CATEGORY_TO_MARKET = {
    "crypto": "crypto",
    "forex": "forex",
}

MARKET_TO_CATEGORY = {v: k for k, v in CATEGORY_TO_MARKET.items()}


async def _get_user_signals_today(
    session: AsyncSession,
    user_id: Optional[str],
    market: str
) -> int:
    """Count signals received today for a user in a specific market"""
    if not user_id:
        return 0

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    stmt = select(func.count(PrinceSignalAlert.id)).where(
        and_(
            PrinceSignalAlert.user_id == user_id,
            PrinceSignalAlert.market == market,
            PrinceSignalAlert.created_at >= today_start
        )
    )

    result = await session.exec(stmt)
    count = result.one() or 0
    return count


async def _is_user_premium(
    session: AsyncSession,
    user_id: Optional[str]
) -> bool:
    """Check if user has active premium subscription"""
    if not user_id:
        return False
    
    try:
        stmt = select(User).where(User.id == user_id)
        result = await session.exec(stmt)
        user = result.first()
        
        if not user:
            return False
        
        # Check if premium is active and not expired
        if user.is_premium and user.premium_expires_at:
            if user.premium_expires_at >= datetime.now(timezone.utc):
                return True
            else:
                # Premium expired - update user
                user.is_premium = False
                user.premium_expires_at = None
                await session.merge(user)
                await session.commit()
                return False
        
        return user.is_premium
    except Exception as e:
        logger.warning(f"Error checking premium status: {e}")
        return False


async def _check_market_availability(
    session: AsyncSession,
    user_id: Optional[str],
    category: str,
    signal_quality: Optional[Dict[str, Any]] = None,
    is_premium: bool = False,
    ad_watched: bool = False
) -> Dict[str, Any]:
    """
    Check if user can receive signals for a specific market category.
    Premium users: 5 signals per market (reasonable limit)
    Free users: 2 base signals per market, can get up to 4 with quality bonuses or ads
    """
    market = CATEGORY_TO_MARKET.get(category.lower(), category.lower())
    base_limit = MARKET_BASE_LIMITS.get(category.lower(), 2)
    max_limit = MARKET_MAX_LIMITS.get(category.lower(), 4)
    
    # Premium users: 5 signals per market (reasonable limit)
    if is_premium:
        premium_limit = PREMIUM_MARKET_LIMITS.get(category.lower(), 5)
        signals_today = await _get_user_signals_today(session, user_id, market)
        remaining = max(0, premium_limit - signals_today)
        
        return {
            "category": category,
            "market": market,
            "base_limit": premium_limit,
            "effective_limit": premium_limit,
            "max_limit": premium_limit,
            "used": signals_today,
            "remaining": remaining,
            "available": remaining > 0,
            "quality_based": False,
            "is_premium": True
        }
    
    signals_today = await _get_user_signals_today(session, user_id, market)
    
    # Determine effective limit based on signal quality and ad watching
    effective_limit = base_limit
    
    # Ad watching grants +1 signal (up to max limit)
    if ad_watched:
        effective_limit = min(base_limit + 1, max_limit)
        logger.info(f"Ad watched - granting bonus signal for {category}. Effective limit: {effective_limit}")
    
    if signal_quality:
        confidence = signal_quality.get("confidence", 0.0)
        risk_reward = signal_quality.get("risk_reward_ratio", 0.0)
        agreeing_strategies = signal_quality.get("agreeing_strategies", 0)
        total_strategies = signal_quality.get("total_strategies", 8)
        
        # Check exceptional quality
        if (confidence >= EXCEPTIONAL_QUALITY_THRESHOLD["confidence_min"] and
            risk_reward >= EXCEPTIONAL_QUALITY_THRESHOLD["risk_reward_min"] and
            agreeing_strategies >= EXCEPTIONAL_QUALITY_THRESHOLD["strategies_agreement"]):
            effective_limit = max_limit
            logger.info(f"Exceptional quality signal detected for {category}")
        
        # Check high quality
        elif (confidence >= HIGH_QUALITY_THRESHOLD["confidence_min"] and
              risk_reward >= HIGH_QUALITY_THRESHOLD["risk_reward_min"] and
              agreeing_strategies >= HIGH_QUALITY_THRESHOLD["strategies_agreement"]):
            effective_limit = min(max(effective_limit, base_limit + 1), max_limit)
            logger.info(f"High quality signal detected for {category}")
    
    remaining = max(0, effective_limit - signals_today)
    
    return {
        "category": category,
        "market": market,
        "base_limit": base_limit,
        "effective_limit": effective_limit,
        "max_limit": max_limit,
        "used": signals_today,
        "remaining": remaining,
        "available": remaining > 0,
        "quality_based": effective_limit > base_limit,
        "ad_bonus": ad_watched
    }


@router.post("/chat")
async def chat_endpoint(
    body: dict,
    session: AsyncSession = Depends(get_session)
):
    """
    Chat with Prince AI.
    Body: { message, userId, context, symbol }
    """
    try:
        message = body.get("message", "")
        user_id = body.get("userId") or body.get("user_id")
        context = body.get("context", {})
        symbol = body.get("symbol")
        
        if not message:
            return {"reply": "Please provide a message.", "error": "empty_message"}
        
        # Use AI service to chat
        response = await ai_service.chat(user_id, message, context)
        
        return {
            "reply": response.get("reply", "I'm here to help with trading questions!"),
            "meta": response.get("meta", {})
        }
    except Exception as e:
        logger.exception(f"Error in chat endpoint: {e}")
        return {
            "reply": "I apologize, but I'm having trouble processing that right now. Please try again.",
            "error": str(e)
        }


@router.post("/analyze")
async def analyze_endpoint(
    body: dict,
    session: AsyncSession = Depends(get_session)
):
    """
    Analyze market and generate signal.
    Body: { symbol, prices?, market?, userId? }
    """
    try:
        symbol = body.get("symbol", "BTCUSDT")
        prices = body.get("prices", [])
        market_type = body.get("market", "crypto")
        user_id = body.get("userId") or body.get("user_id")
        
        # Generate signal using Prince AI
        signal_data = await prince_ai.generate_loss_averse_signal(
            symbol=symbol,
            prices=prices,
            user_risk_profile="Medium",
            user_id=user_id,
            market_type=market_type
        )
        
        return {
            "success": True,
            "signal": signal_data
        }
    except Exception as e:
        logger.exception(f"Error in analyze endpoint: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/status")
async def signal_status_endpoint(
    session: AsyncSession = Depends(get_session),
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """
    Get daily signal status showing per-market availability.
    """
    try:
        user_id = None
        if authorization and authorization.startswith("Bearer "):
            try:
                token = authorization.replace("Bearer ", "")
                current_user_obj = await get_current_user(token, session)
                user_id = current_user_obj.id if current_user_obj else None
            except Exception:
                pass
        
        is_premium = await _is_user_premium(session, user_id)
        
        # Check all markets
        markets_status = {}
        for category in MARKET_BASE_LIMITS.keys():
            status = await _check_market_availability(session, user_id, category, is_premium=is_premium)
            markets_status[category] = status
        
        total_used = sum(s["used"] for s in markets_status.values())
        total_base_limit = sum(s["base_limit"] for s in markets_status.values())
        total_remaining = sum(s["remaining"] for s in markets_status.values())
        
        overall_available = total_remaining > 0
        
        return {
            "success": True,
            "available": overall_available,
            "remaining": total_remaining,
            "daily_limit": total_base_limit,
            "used": total_used,
            "markets": markets_status,
            "message": "Signal availability status" if overall_available else "Daily signal limit reached for all markets"
        }
    except Exception as e:
        logger.exception(f"Error in signal status endpoint: {e}")
        return {
            "success": True,
            "available": True,
            "remaining": 1,
            "daily_limit": 8,
            "used": 0,
            "markets": {
                cat: {
                    "base_limit": 2,
                    "effective_limit": 2,
                    "max_limit": 4,
                    "used": 0,
                    "remaining": 2,
                    "available": True,
                    "quality_based": False
                }
                for cat in MARKET_BASE_LIMITS.keys()
            },
            "message": "Status check unavailable, assuming available"
        }


@router.get("/signal")
async def get_signal_endpoint(
    category: str = Query(..., description="Market category: crypto, forex"),
    ad_watched: bool = Query(False, description="Set to true if user watched ad for bonus signal"),
    session: AsyncSession = Depends(get_session),
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """
    Get AI signal for a specific market category with per-market daily limits.
    Premium users: 5 signals per market
    Free users: 2 base signals per market, can get up to 4 with quality bonuses or ads
    """
    try:
        category_lower = category.lower()
        
        if category_lower not in CATEGORY_TO_MARKET:
            return {
                "success": False,
                "category_unavailable": True,
                "message": f"Invalid category '{category}'. Valid categories: crypto, forex",
            }
        
        market = CATEGORY_TO_MARKET[category_lower]
        
        # Get user from Authorization header
        user_id = None
        if authorization and authorization.startswith("Bearer "):
            try:
                token = authorization.replace("Bearer ", "")
                current_user_obj = await get_current_user(token, session)
                user_id = current_user_obj.id if current_user_obj else None
            except Exception:
                pass
        
        is_premium = await _is_user_premium(session, user_id)
        
        # Initial availability check
        initial_check = await _check_market_availability(
            session, user_id, category_lower, 
            is_premium=is_premium, ad_watched=ad_watched
        )
        signals_today = initial_check["used"]
        premium_limit = PREMIUM_MARKET_LIMITS.get(category_lower, 5) if is_premium else None
        
        # Check limits before generating signal
        if is_premium:
            if signals_today >= premium_limit:
                alternatives = []
                for alt_cat, alt_market in CATEGORY_TO_MARKET.items():
                    if alt_cat != category_lower:
                        alt_status = await _check_market_availability(session, user_id, alt_cat, is_premium=is_premium)
                        if alt_status["available"]:
                            alternatives.append(alt_cat)
                
                return {
                    "success": False,
                    "category_unavailable": True,
                    "message": f"Daily signal limit ({premium_limit}) reached for {category_lower.capitalize()}. Try again tomorrow or try another market.",
                    "suggested_category": alternatives[0] if alternatives else None,
                    "alternative_categories": alternatives
                }
        else:
            # Free user - check base limits
            if signals_today >= initial_check["effective_limit"]:
                if not initial_check.get("quality_based") and not ad_watched:
                    alternatives = []
                    for alt_cat, alt_market in CATEGORY_TO_MARKET.items():
                        if alt_cat != category_lower:
                            alt_status = await _check_market_availability(session, user_id, alt_cat, is_premium=is_premium)
                            if alt_status["available"]:
                                alternatives.append(alt_cat)
                    
                    return {
                        "success": False,
                        "category_unavailable": True,
                        "message": f"Daily signal limit ({initial_check['effective_limit']}) reached for {category_lower.capitalize()}. Watch an ad or upgrade to Premium.",
                        "suggested_category": alternatives[0] if alternatives else None,
                        "alternative_categories": alternatives
                    }
        
        # Get default symbol for market
        default_symbols = {
            "crypto": "BTCUSDT",
            "forex": "EURUSD",
        }
        symbol = default_symbols.get(category_lower, "BTCUSDT")
        
        # Generate signal
        signal_data = await prince_ai.generate_loss_averse_signal(
            symbol=symbol,
            prices=[],
            user_risk_profile="Medium",
            user_id=user_id,
            market_type=market
        )
        
        if not signal_data.get("passed_filters"):
            return {
                "success": False,
                "message": f"No optimal setup found in {category_lower.capitalize()} market right now. Try again later.",
                "category_unavailable": True
            }
        
        # Re-check availability with signal quality
        signal_quality = {
            "confidence": signal_data.get("confidence", 0.0),
            "risk_reward_ratio": signal_data.get("risk_reward_ratio", 0.0),
            "agreeing_strategies": signal_data.get("agreeing_strategies", 0),
            "total_strategies": signal_data.get("total_strategies", 8),
            "strength": signal_data.get("strength", 0.0)
        }
        
        quality_check = await _check_market_availability(
            session, user_id, category_lower, signal_quality, 
            is_premium=is_premium, ad_watched=ad_watched
        )
        
        # Final limit check
        if not is_premium:
            if signals_today >= quality_check["effective_limit"]:
                if not quality_check.get("quality_based"):
                    return {
                        "success": False,
                        "category_unavailable": True,
                        "message": f"Daily signal limit ({quality_check['effective_limit']}) reached for {category_lower.capitalize()}.",
                    }
        
        # Save signal for user
        if user_id:
            await prince_ai.save_signal(symbol, signal_data, user_id, market=market)
        
        # Format response
        action = signal_data.get("signal", "hold")
        confidence = signal_data.get("confidence", 0.5)
        
        prince_msg = signal_data.get("message", "")
        if not prince_msg:
            prince_msg = f"Prince AI found a {action.upper()} signal for {symbol} in {category_lower.capitalize()} market."
        
        # Add quality indicator
        is_quality_bonus = quality_check.get("quality_based", False) if not is_premium else False
        quality_note = ""
        if is_quality_bonus:
            if quality_check["effective_limit"] >= quality_check["max_limit"]:
                quality_note = " 🏆 Exceptional quality signal!"
            else:
                quality_note = " ⭐ High quality signal!"
        
        disclaimer = " ⚠️ AI Prince signals are for educational purposes only."
        
        return {
            "success": True,
            "signal": prince_msg + quality_note + disclaimer,
            "action": action,
            "confidence": confidence,
            "rationale": signal_data.get("rationale", ""),
            "quality_bonus": is_quality_bonus,
            "ad_bonus": ad_watched
        }
        
    except Exception as e:
        logger.exception(f"Error in get_signal endpoint: {e}")
        return {
            "success": False,
            "message": f"Error generating signal: {str(e)}"
        }


@router.post("/startup-ad-watched")
async def startup_ad_watched_endpoint(
    session: AsyncSession = Depends(get_session),
    authorization: Optional[str] = Header(None, alias="Authorization")
):
    """
    Grant signals when user watches startup ad.
    Free users: 2 signals total
    Premium users: 5 signals total
    Note: These are available when requesting signals, not automatically granted.
    """
    try:
        user_id = None
        if authorization and authorization.startswith("Bearer "):
            try:
                token = authorization.replace("Bearer ", "")
                current_user_obj = await get_current_user(token, session)
                user_id = current_user_obj.id if current_user_obj else None
            except Exception:
                pass
        
        if not user_id:
            return {
                "success": False,
                "message": "User authentication required"
            }
        
        is_premium = await _is_user_premium(session, user_id)
        
        # Get total signals today across all markets
        total_signals_today = 0
        for market in CATEGORY_TO_MARKET.values():
            count = await _get_user_signals_today(session, user_id, market)
            total_signals_today += count
        
        # If user already has signals today, they've already used startup ad
        if total_signals_today > 0:
            return {
                "success": True,
                "message": "Startup ad already credited today",
                "signals_granted": 0,
                "is_premium": is_premium
            }
        
        # Grant signals: Free users get 2, Premium users get 5
        signals_to_grant = 5 if is_premium else 2
        
        return {
            "success": True,
            "message": f"Startup ad watched! {signals_to_grant} signals granted.",
            "signals_granted": signals_to_grant,
            "is_premium": is_premium,
            "note": "These signals will be available when you request signals from Prince AI"
        }
        
    except Exception as e:
        logger.error(f"Error processing startup ad: {e}")
        return {
            "success": False,
            "message": f"Error processing startup ad: {str(e)}"
        }
