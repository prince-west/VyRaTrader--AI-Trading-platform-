"""
Risk management module for VyRaTrader.
- Position sizing based on account balance and risk parameters
- Risk parity allocation across strategies
- Drawdown protection and kill-switch functionality
"""

from __future__ import annotations

import math
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

import numpy as np
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from backend.app.core.logger import logger
from backend.app.db.models import Trade, Account


# Risk profile mappings
RISK_MAP = {
    "Low": {"risk_multiplier": 0.3, "max_vol_alloc": 0.10, "stop_loss_pct": 0.03},
    "Medium": {"risk_multiplier": 0.6, "max_vol_alloc": 0.25, "stop_loss_pct": 0.07},
    "High": {"risk_multiplier": 1.0, "max_vol_alloc": 0.60, "stop_loss_pct": 0.15},
}


def kelly_fraction(win_rate: float, win_loss_ratio: float) -> float:
    """Calculate Kelly criterion position sizing fraction."""
    # simplified Kelly: f* = (bp - q)/b where p=win_rate q=1-p b=win_loss_ratio
    p = win_rate
    q = 1 - p
    b = win_loss_ratio
    if b <= 0:
        return 0.0
    f = (b * p - q) / b
    return max(0.0, min(1.0, f))


def position_sizing(
    account_balance: float,
    risk_pct: float,
    stop_distance_atr: float,
    volatility_scale: float = 1.0
) -> float:
    """
    Calculate position size based on account balance, risk percentage, and stop distance.
    
    Args:
        account_balance: Total account balance
        risk_pct: Risk percentage per trade (e.g., 0.02 for 2%)
        stop_distance_atr: Stop loss distance in ATR units
        volatility_scale: Volatility scaling factor (higher = smaller positions)
    
    Returns:
        Position size in base currency
    """
    if account_balance <= 0 or risk_pct <= 0 or stop_distance_atr <= 0:
        return 0.0
    
    # Risk amount in currency
    risk_amount = account_balance * risk_pct
    
    # Position size = Risk Amount / Stop Distance
    # Adjusted by volatility scale
    position_size = (risk_amount / stop_distance_atr) * (1.0 / volatility_scale)
    
    # Cap position size to reasonable limits
    max_position = account_balance * 0.1  # Max 10% of account
    position_size = min(position_size, max_position)
    
    return max(0.0, position_size)


def risk_parity_allocator(strategy_signals: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Allocate capital across strategies using risk parity (inverse volatility weighting).
    
    Args:
        strategy_signals: List of strategy signals with 'strategy' and 'confidence' fields
    
    Returns:
        Dictionary mapping strategy names to allocation weights
    """
    if not strategy_signals:
        return {}
    
    # Extract strategy names and confidences
    strategies = {}
    for signal in strategy_signals:
        strategy_name = signal.get("strategy", "unknown")
        confidence = signal.get("confidence", 0.0)
        
        # Use inverse of (1 - confidence) as volatility proxy
        # Higher confidence = lower volatility = higher weight
        volatility_proxy = max(0.1, 1.0 - confidence)  # Avoid division by zero
        
        if strategy_name not in strategies:
            strategies[strategy_name] = []
        strategies[strategy_name].append(volatility_proxy)
    
    # Calculate average volatility proxy for each strategy
    strategy_volatilities = {}
    for strategy_name, volatilities in strategies.items():
        avg_volatility = np.mean(volatilities)
        strategy_volatilities[strategy_name] = avg_volatility
    
    # Calculate inverse volatility weights
    inverse_volatilities = {}
    total_inverse_vol = 0.0
    
    for strategy_name, volatility in strategy_volatilities.items():
        inverse_vol = 1.0 / volatility
        inverse_volatilities[strategy_name] = inverse_vol
        total_inverse_vol += inverse_vol
    
    # Normalize to get allocation weights
    allocations = {}
    if total_inverse_vol > 0:
        for strategy_name, inverse_vol in inverse_volatilities.items():
            weight = inverse_vol / total_inverse_vol
            allocations[strategy_name] = weight
    
    return allocations


class DrawdownProtection:
    """Drawdown protection and kill-switch functionality."""
    
    def __init__(
        self,
        max_drawdown_pct: float = 0.15,  # 15% max drawdown
        lookback_days: int = 30,
        reduction_factor: float = 0.5,  # Reduce allocations by 50% when triggered
    ):
        self.max_drawdown_pct = max_drawdown_pct
        self.lookback_days = lookback_days
        self.reduction_factor = reduction_factor
        self.kill_switch_active = False
    
    async def calculate_drawdown(
        self, 
        session: AsyncSession, 
        user_id: str
    ) -> Dict[str, float]:
        """Calculate current drawdown for a user."""
        try:
            # Get account balance
            stmt = select(Account).where(Account.user_id == user_id)
            result = await session.exec(stmt)
            account = result.first()
            
            if not account:
                return {"current_drawdown": 0.0, "peak_balance": 0.0, "current_balance": 0.0}
            
            current_balance = account.available_balance
            
            # Get historical trades to calculate peak balance
            cutoff_date = datetime.utcnow() - timedelta(days=self.lookback_days)
            stmt = select(Trade).where(
                and_(
                    Trade.user_id == user_id,
                    Trade.opened_at >= cutoff_date
                )
            ).order_by(Trade.opened_at)
            
            result = await session.exec(stmt)
            trades = result.all()
            
            if not trades:
                return {"current_drawdown": 0.0, "peak_balance": current_balance, "current_balance": current_balance}
            
            # Calculate running balance (simplified - assumes starting balance)
            # In practice, you'd want to track actual balance history
            peak_balance = current_balance
            running_balance = current_balance
            
            for trade in reversed(trades):  # Go backwards from most recent
                if trade.profit_loss is not None:
                    running_balance -= trade.profit_loss
                    peak_balance = max(peak_balance, running_balance)
            
            # Calculate drawdown
            if peak_balance > 0:
                current_drawdown = (peak_balance - current_balance) / peak_balance
            else:
                current_drawdown = 0.0
            
            return {
                "current_drawdown": current_drawdown,
                "peak_balance": peak_balance,
                "current_balance": current_balance
            }
            
        except Exception as exc:
            logger.exception(f"Error calculating drawdown for user {user_id}: {exc}")
            return {"current_drawdown": 0.0, "peak_balance": 0.0, "current_balance": 0.0}
    
    async def check_kill_switch(
        self, 
        session: AsyncSession, 
        user_id: str
    ) -> Dict[str, Any]:
        """Check if kill switch should be activated based on drawdown."""
        drawdown_info = await self.calculate_drawdown(session, user_id)
        current_drawdown = drawdown_info["current_drawdown"]
        
        should_activate = current_drawdown > self.max_drawdown_pct
        
        if should_activate and not self.kill_switch_active:
            self.kill_switch_active = True
            logger.warning(f"Kill switch activated for user {user_id}: drawdown {current_drawdown:.2%}")
        
        return {
            "kill_switch_active": self.kill_switch_active,
            "current_drawdown": current_drawdown,
            "max_drawdown": self.max_drawdown_pct,
            "drawdown_info": drawdown_info
        }
    
    def apply_drawdown_protection(
        self, 
        allocations: Dict[str, float]
    ) -> Dict[str, float]:
        """Apply drawdown protection to strategy allocations."""
        if not self.kill_switch_active:
            return allocations
        
        # Reduce all allocations by reduction factor
        protected_allocations = {}
        for strategy, weight in allocations.items():
            protected_allocations[strategy] = weight * self.reduction_factor
        
        return protected_allocations
    
    def reset_kill_switch(self) -> None:
        """Reset kill switch (typically after manual review)."""
        self.kill_switch_active = False
        logger.info("Kill switch reset")


class RiskManager:
    """Main risk management class combining all risk functions."""
    
    def __init__(self, drawdown_protection: Optional[DrawdownProtection] = None):
        self.drawdown_protection = drawdown_protection or DrawdownProtection()
    
    def apply(
        self, 
        ensemble_decision: Dict[str, Any], 
        account_balance: float, 
        user_risk: str = "Medium"
    ) -> Dict[str, Any]:
        """
        Apply risk management to ensemble decision.
        
        Args:
            ensemble_decision: Strategy signal with 'signal', 'size', etc.
            account_balance: Account balance in base currency
            user_risk: Risk profile (Low/Medium/High)
        
        Returns:
            Augmented decision with position sizing and risk parameters
        """
        rp = RISK_MAP.get(user_risk, RISK_MAP["Medium"])
        base_fraction = ensemble_decision.get("size", 0.1)  # fraction suggested by ensemble
        risk_mult = rp["risk_multiplier"]
        
        # Position fraction of equity
        fraction = max(0.01, min(1.0, base_fraction * risk_mult))
        # Enforce max volatile allocation
        fraction = min(fraction, rp["max_vol_alloc"])
        position_size = account_balance * fraction
        
        ensemble_decision["position_size"] = position_size
        ensemble_decision["risk_params"] = rp
        
        return ensemble_decision
    
    async def apply_comprehensive_risk_management(
        self,
        session: AsyncSession,
        strategy_signals: List[Dict[str, Any]],
        user_id: str,
        account_balance: float,
        user_risk: str = "Medium"
    ) -> Dict[str, Any]:
        """Apply comprehensive risk management including drawdown protection."""
        # Check kill switch
        kill_switch_info = await self.drawdown_protection.check_kill_switch(session, user_id)
        
        # Calculate risk parity allocations
        allocations = risk_parity_allocator(strategy_signals)
        
        # Apply drawdown protection if needed
        if kill_switch_info["kill_switch_active"]:
            allocations = self.drawdown_protection.apply_drawdown_protection(allocations)
        
        # Apply individual position sizing
        risk_managed_signals = []
        for signal in strategy_signals:
            strategy_name = signal.get("strategy", "unknown")
            allocation_weight = allocations.get(strategy_name, 0.0)
            
            if allocation_weight > 0:
                # Calculate position size for this strategy
                risk_pct = 0.02  # 2% risk per trade
                stop_distance = signal.get("sl", 0.0)
                entry_price = signal.get("entry", 0.0)
                
                if stop_distance > 0 and entry_price > 0:
                    stop_distance_atr = abs(entry_price - stop_distance) / entry_price
                    pos_size = position_sizing(account_balance, risk_pct, stop_distance_atr)
                    signal["position_size"] = pos_size * allocation_weight
                else:
                    signal["position_size"] = 0.0
                
                risk_managed_signals.append(signal)
        
        return {
            "signals": risk_managed_signals,
            "allocations": allocations,
            "kill_switch_info": kill_switch_info,
            "total_allocated": sum(allocations.values())
        }


# Convenience functions for external use
def calculate_position_size(
    account_balance: float,
    risk_pct: float,
    stop_distance_atr: float,
    volatility_scale: float = 1.0
) -> float:
    """Calculate position size based on risk parameters."""
    return position_sizing(account_balance, risk_pct, stop_distance_atr, volatility_scale)


def allocate_strategies(strategy_signals: List[Dict[str, Any]]) -> Dict[str, float]:
    """Allocate capital across strategies using risk parity."""
    return risk_parity_allocator(strategy_signals)
