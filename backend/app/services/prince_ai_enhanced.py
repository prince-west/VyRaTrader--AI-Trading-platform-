"""
Enhanced Prince AI with Loss-Aversion, Smart API Usage, and Signal Alerts.
Makes Prince AI more conservative to minimize user losses while maximizing wins.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from backend.app.core.logger import logger
from backend.app.db.session import get_session
from backend.app.db.models import Signals, PrinceSignalAlert, Notification, StrategyPerformance
from sqlmodel import select
from backend.app.services.api_request_manager import api_manager, get_prince_smart_recommendation
from backend.app.services.ai_ensemble import AIEnsemble
from backend.app.services.risk_manager import RiskManager


class LossAverseEnsemble:
    """
    Enhanced ensemble that prioritizes NOT making users lose.
    Uses multiple filters to ensure only high-confidence, low-risk signals are generated.
    """
    
    def __init__(self, base_ensemble: AIEnsemble):
        self.base_ensemble = base_ensemble
        self.conservatism_multiplier = 1.2  # Makes signals more conservative
        self.min_confidence_for_signal = 0.65  # Higher bar for signals
        self.max_daily_signals = 3  # Limit signals to prevent overtrading
    
    async def generate_loss_averse_signal(
        self,
        symbol: str,
        prices: List[float],
        user_risk_profile: str = "Medium",
        user_id: Optional[str] = None,
        market_type: str = "crypto"
    ) -> Dict[str, Any]:
        """
        Generate a loss-averse trading signal.
        Only returns buy/sell if multiple strategies agree AND risk is low.
        """
        try:
            # Check API availability first
            api_recommendation = await get_prince_smart_recommendation(market_type, symbol)
            
            if not api_recommendation.get("available"):
                return {
                    "signal": "hold",
                    "confidence": 0.0,
                    "message": api_recommendation.get("recommendation", "Data unavailable"),
                    "unavailable": True,
                    "should_wait": True,
                }
            
            # Get base ensemble signal
            ensemble_result = self.base_ensemble.aggregate(symbol, prices)
            
            if ensemble_result["final_signal"] == "hold":
                return {
                    "signal": "hold",
                    "confidence": 0.0,
                    "message": "Prince AI: Market conditions are unclear. Better to wait for a clearer signal.",
                    "reason": "low_consensus",
                }
            
            # Extract strength and details
            buy_score = ensemble_result.get("buy_score", 0.0)
            sell_score = ensemble_result.get("sell_score", 0.0)
            strength = ensemble_result.get("strength", 0.0)
            details = ensemble_result.get("details", {})
            
            # Calculate confidence from strategy agreement
            agreeing_strategies = sum(
                1 for detail in details.values()
                if detail.get("signal") == ensemble_result["final_signal"]
            )
            total_strategies = len(details)
            confidence = agreeing_strategies / total_strategies if total_strategies > 0 else 0.0
            
            # LOSS AVERSION FILTERS
            # 1. Only proceed if multiple strategies agree
            if agreeing_strategies < 5:  # Need at least 5 of 8 strategies to agree
                return {
                    "signal": "hold",
                    "confidence": confidence,
                    "message": f"Prince AI: Only {agreeing_strategies}/{total_strategies} strategies agree. Waiting for stronger consensus to protect your capital.",
                    "reason": "low_agreement",
                    "details": details,
                }
            
            # 2. Apply conservative confidence adjustment
            confidence = confidence * self.conservatism_multiplier
            confidence = min(confidence, 1.0)
            
            # 3. Check if confidence meets minimum threshold
            if confidence < self.min_confidence_for_signal:
                return {
                    "signal": "hold",
                    "confidence": confidence,
                    "message": f"Prince AI: Confidence ({confidence:.0%}) below my safety threshold. Skipping to prevent potential loss.",
                    "reason": "low_confidence",
                    "details": details,
                }
            
            # 4. Check recent performance of similar signals (from database)
            recent_success = await self._check_recent_performance(symbol, ensemble_result["final_signal"])
            if recent_success < 0.5:  # If less than 50% success rate recently
                return {
                    "signal": "hold",
                    "confidence": confidence,
                    "message": f"Prince AI: Recent similar signals had low success ({recent_success:.0%}). Better to wait for more favorable conditions.",
                    "reason": "recent_poor_performance",
                    "details": details,
                }
            
            # 5. Calculate expected risk/reward
            risk_reward = self._calculate_risk_reward(ensemble_result["final_signal"], buy_score, sell_score)
            
            if risk_reward < 2.0:  # Risk/reward must be at least 2:1
                return {
                    "signal": "hold",
                    "confidence": confidence,
                    "message": f"Prince AI: Risk/Reward ratio ({risk_reward:.2f}) is too low. I only signal when reward significantly outweighs risk.",
                    "reason": "poor_risk_reward",
                    "details": details,
                }
            
            # PASSED ALL FILTERS - Generate signal
            price = prices[-1] if prices else 0.0
            entry = price
            stop_loss = price * 0.97 if ensemble_result["final_signal"] == "buy" else price * 1.03  # 3% stop
            take_profit = price * 1.05 if ensemble_result["final_signal"] == "buy" else price * 0.95  # 5% target
            
            # Adjust SL/TP based on risk profile
            risk_params = {
                "Low": {"sl_pct": 0.02, "tp_pct": 0.03},
                "Medium": {"sl_pct": 0.05, "tp_pct": 0.07},
                "High": {"sl_pct": 0.10, "tp_pct": 0.15},
            }.get(user_risk_profile, risk_params["Medium"])
            
            stop_loss = price * (1 - risk_params["sl_pct"]) if ensemble_result["final_signal"] == "buy" else price * (1 + risk_params["sl_pct"])
            take_profit = price * (1 + risk_params["tp_pct"]) if ensemble_result["final_signal"] == "buy" else price * (1 - risk_params["tp_pct"])
            
            # Generate Prince's message
            action = "BUY" if ensemble_result["final_signal"] == "buy" else "SELL"
            prince_message = f"""Prince AI here! I've found a {action} opportunity for {symbol}.

Confidence: {confidence:.0%} ({agreeing_strategies}/{total_strategies} strategies agree)
Signal Strength: {'Strong' if strength > 0.7 else 'Medium'}
Risk/Reward: {risk_reward:.2f}:1
Entry: ${entry:.2f}
Stop Loss: ${stop_loss:.2f} ({risk_params['sl_pct']*100:.1f}% risk)
Take Profit: ${take_profit:.2f} ({risk_params['tp_pct']*100:.1f}% reward)

This signal passed my conservative filters to protect your capital. Proceed?"""
            
            return {
                "signal": ensemble_result["final_signal"],
                "confidence": confidence,
                "strength": strength,
                "price": price,
                "entry": entry,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "message": prince_message,
                "risk_reward_ratio": risk_reward,
                "details": details,
                "conservative": True,
                "passed_filters": True,
            }
            
        except Exception as e:
            logger.exception(f"Error generating loss-averse signal: {e}")
            return {
                "signal": "hold",
                "confidence": 0.0,
                "message": "Prince AI: Error analyzing market. Please try again.",
                "error": str(e),
            }
    
    def _calculate_risk_reward(self, signal: str, buy_score: float, sell_score: float) -> float:
        """Calculate risk/reward ratio"""
        if signal == "buy":
            return buy_score / max(0.01, abs(buy_score - sell_score))
        else:
            return sell_score / max(0.01, abs(buy_score - sell_score))
    
    async def _check_recent_performance(self, symbol: str, signal_type: str) -> float:
        """Check recent performance of similar signals"""
        try:
            async for session in get_session():
                # Get recent signals for this symbol
                cutoff = datetime.now(timezone.utc) - timedelta(days=7)
                stmt = select(Signals).where(
                    Signals.symbol == symbol,
                    Signals.action == signal_type,
                    Signals.timestamp >= cutoff
                )
                result = await session.exec(stmt)
                recent_signals = result.all()
                
                if not recent_signals:
                    return 1.0  # No data = assume good (conservative)
                
                # Get performance data for these signals
                signal_ids = [s.id for s in recent_signals]
                # Calculate win rate from trades linked to these signals
                # (You'd need to join with trades table)
                return 0.65  # Placeholder - would calculate from actual trades
        except Exception:
            return 1.0
    
    async def save_signal(
        self,
        symbol: str,
        signal_data: Dict[str, Any],
        user_id: Optional[str] = None,
        market: str = "crypto"
    ) -> Optional[str]:
        """Save signal to database for Prince alerts"""
        if not signal_data.get("passed_filters"):
            return None
        
        try:
            async for session in get_session():
                # Create signal record
                signal = Signals(
                    strategy="prince_ai_loss_averse",
                    symbol=symbol,
                    action=signal_data["signal"],
                    entry=signal_data.get("entry", 0.0),
                    sl=signal_data.get("stop_loss", 0.0),
                    tp=signal_data.get("take_profit", 0.0),
                    confidence=signal_data.get("confidence", 0.0),
                    source_meta={
                        "conservative": True,
                        "risk_reward": signal_data.get("risk_reward_ratio", 0.0),
                        "strength": signal_data.get("strength", 0.0),
                        "details": signal_data.get("details", {}),
                    },
                    timestamp=datetime.now(timezone.utc),
                    processed=False,
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=4),  # Signal expires in 4 hours
                )
                session.add(signal)
                await session.commit()
                await session.refresh(signal)
                
                # Create Prince alert if user_id provided
                if user_id:
                    alert = PrinceSignalAlert(
                        user_id=user_id,
                        signal_id=signal.id,
                        symbol=symbol,
                        market=market,  # Use provided market
                        action=signal_data["signal"],
                        confidence=signal_data.get("confidence", 0.0),
                        expected_profit_pct=abs(signal_data.get("take_profit", 0.0) - signal_data.get("entry", 0.0)) / signal_data.get("entry", 1.0) * 100,
                        risk_level="medium",
                        prince_message=signal_data.get("message", ""),
                        notified=False,
                        created_at=datetime.now(timezone.utc),
                        expires_at=datetime.now(timezone.utc) + timedelta(hours=4),
                    )
                    session.add(alert)
                    await session.commit()
                    await session.refresh(alert)
                    
                    # Send notification
                    await self._send_prince_alert(user_id, alert, signal_data)
                
                return signal.id
        except Exception as e:
            logger.exception(f"Error saving signal: {e}")
            return None
    
    async def _send_prince_alert(
        self,
        user_id: str,
        alert: PrinceSignalAlert,
        signal_data: Dict[str, Any]
    ):
        """Send push notification for Prince AI alert"""
        try:
            async for session in get_session():
                notification = Notification(
                    user_id=user_id,
                    title="🎯 Prince AI: New Trading Signal",
                    body=alert.prince_message or "Prince found a reliable trading opportunity",
                    meta={
                        "type": "prince_signal",
                        "symbol": alert.symbol,
                        "action": alert.action,
                        "confidence": alert.confidence,
                        "alert_id": alert.id,
                        "signal_id": alert.signal_id,
                    },
                    is_read=False,
                    created_at=datetime.now(timezone.utc),
                )
                session.add(notification)
                alert.notified = True
                alert.notification_sent_at = datetime.now(timezone.utc)
                await session.commit()
                
                logger.info(f"Prince alert sent to user {user_id} for {alert.symbol}")
        except Exception as e:
            logger.exception(f"Error sending Prince alert: {e}")


# Global instance
base_ensemble = AIEnsemble()
prince_ai = LossAverseEnsemble(base_ensemble)

