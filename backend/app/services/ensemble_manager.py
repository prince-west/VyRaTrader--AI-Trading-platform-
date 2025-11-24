"""
Meta-learner and ensemble manager for VyRaTrader.
- Tracks historical performance of each strategy using AILog and Performance tables
- Calculates dynamic weights via simple logistic/Sharpe-based weighting
- Exposes get_weighted_signal() for unified signal with combined confidence
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

import numpy as np
from sqlmodel import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logger import logger
from backend.app.db.models import AILog, Trade, Strategy


class StrategyPerformanceTracker:
    """Tracks and calculates performance metrics for each strategy."""
    
    def __init__(self, lookback_days: int = 30):
        self.lookback_days = lookback_days
    
    async def get_strategy_trades(
        self, 
        session: AsyncSession, 
        strategy_name: str,
        user_id: Optional[str] = None
    ) -> List[Trade]:
        """Get recent trades for a specific strategy."""
        cutoff_date = datetime.utcnow() - timedelta(days=self.lookback_days)
        
        conditions = [
            Trade.strategy == strategy_name,
            Trade.opened_at >= cutoff_date,
            Trade.status == "closed"  # Only completed trades
        ]
        
        if user_id:
            conditions.append(Trade.user_id == user_id)
        
        stmt = select(Trade).where(and_(*conditions)).order_by(Trade.opened_at)
        result = await session.exec(stmt)
        return result.all()
    
    async def calculate_strategy_metrics(
        self, 
        session: AsyncSession, 
        strategy_name: str,
        user_id: Optional[str] = None
    ) -> Dict[str, float]:
        """Calculate performance metrics for a strategy."""
        trades = await self.get_strategy_trades(session, strategy_name, user_id)
        
        if not trades:
            return {
                "win_rate": 0.0,
                "avg_return": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "total_trades": 0,
                "profit_factor": 0.0,
                "recent_performance": 0.0
            }
        
        # Extract returns
        returns = []
        profits = []
        losses = []
        running_balance = 0.0
        peak_balance = 0.0
        max_drawdown = 0.0
        
        for trade in trades:
            if trade.profit_loss is not None:
                returns.append(trade.profit_loss)
                running_balance += trade.profit_loss
                peak_balance = max(peak_balance, running_balance)
                
                current_drawdown = (peak_balance - running_balance) / peak_balance if peak_balance > 0 else 0.0
                max_drawdown = max(max_drawdown, current_drawdown)
                
                if trade.profit_loss > 0:
                    profits.append(trade.profit_loss)
                else:
                    losses.append(abs(trade.profit_loss))
        
        if not returns:
            return {
                "win_rate": 0.0,
                "avg_return": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "total_trades": len(trades),
                "profit_factor": 0.0,
                "recent_performance": 0.0
            }
        
        # Calculate metrics
        total_trades = len(returns)
        winning_trades = len(profits)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        avg_return = np.mean(returns)
        return_std = np.std(returns) if len(returns) > 1 else 0.0
        
        # Sharpe ratio (simplified - using return std as volatility proxy)
        sharpe_ratio = avg_return / return_std if return_std > 0 else 0.0
        
        # Profit factor
        total_profits = sum(profits) if profits else 0.0
        total_losses = sum(losses) if losses else 0.0
        profit_factor = total_profits / total_losses if total_losses > 0 else float('inf') if total_profits > 0 else 0.0
        
        # Recent performance (last 7 days)
        recent_cutoff = datetime.utcnow() - timedelta(days=7)
        recent_returns = [
            trade.profit_loss for trade in trades 
            if trade.closed_at and trade.closed_at >= recent_cutoff and trade.profit_loss is not None
        ]
        recent_performance = np.mean(recent_returns) if recent_returns else 0.0
        
        return {
            "win_rate": float(win_rate),
            "avg_return": float(avg_return),
            "sharpe_ratio": float(sharpe_ratio),
            "max_drawdown": float(max_drawdown),
            "total_trades": total_trades,
            "profit_factor": float(profit_factor) if profit_factor != float('inf') else 10.0,  # Cap at 10
            "recent_performance": float(recent_performance)
        }
    
    async def get_all_strategy_metrics(
        self, 
        session: AsyncSession,
        user_id: Optional[str] = None
    ) -> Dict[str, Dict[str, float]]:
        """Get performance metrics for all strategies."""
        # Get all active strategies
        stmt = select(Strategy).where(Strategy.is_active == True)
        result = await session.exec(stmt)
        strategies = result.all()
        
        metrics = {}
        for strategy in strategies:
            strategy_metrics = await self.calculate_strategy_metrics(
                session, strategy.name, user_id
            )
            metrics[strategy.name] = strategy_metrics
        
        return metrics


class EnsembleWeightCalculator:
    """Calculates dynamic weights for strategy ensemble."""
    
    def __init__(
        self,
        sharpe_weight: float = 0.4,
        win_rate_weight: float = 0.3,
        recent_performance_weight: float = 0.2,
        profit_factor_weight: float = 0.1,
        min_trades_threshold: int = 5
    ):
        self.sharpe_weight = sharpe_weight
        self.win_rate_weight = win_rate_weight
        self.recent_performance_weight = recent_performance_weight
        self.profit_factor_weight = profit_factor_weight
        self.min_trades_threshold = min_trades_threshold
    
    def normalize_metric(self, value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
        """Normalize a metric to [0, 1] range."""
        if max_val <= min_val:
            return 0.0
        return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))
    
    def calculate_strategy_score(self, metrics: Dict[str, float]) -> float:
        """Calculate a composite score for a strategy based on multiple metrics."""
        # Check if strategy has enough trades
        if metrics.get("total_trades", 0) < self.min_trades_threshold:
            return 0.0
        
        # Normalize metrics
        win_rate = self.normalize_metric(metrics.get("win_rate", 0.0), 0.0, 1.0)
        sharpe_ratio = self.normalize_metric(metrics.get("sharpe_ratio", 0.0), -2.0, 2.0)
        profit_factor = self.normalize_metric(metrics.get("profit_factor", 0.0), 0.0, 3.0)
        
        # Recent performance (can be negative, so normalize differently)
        recent_perf = metrics.get("recent_performance", 0.0)
        recent_perf_normalized = self.normalize_metric(recent_perf, -0.1, 0.1)  # -10% to +10%
        
        # Calculate weighted score
        score = (
            win_rate * self.win_rate_weight +
            sharpe_ratio * self.sharpe_weight +
            recent_perf_normalized * self.recent_performance_weight +
            profit_factor * self.profit_factor_weight
        )
        
        return max(0.0, score)  # Ensure non-negative
    
    def calculate_weights(self, strategy_metrics: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        """Calculate dynamic weights for all strategies."""
        if not strategy_metrics:
            return {}
        
        # Calculate scores for each strategy
        strategy_scores = {}
        for strategy_name, metrics in strategy_metrics.items():
            score = self.calculate_strategy_score(metrics)
            strategy_scores[strategy_name] = score
        
        # Convert scores to weights using softmax-like function
        total_score = sum(strategy_scores.values())
        if total_score <= 0:
            # Equal weights if no positive scores
            num_strategies = len(strategy_scores)
            return {name: 1.0 / num_strategies for name in strategy_scores.keys()}
        
        # Calculate weights
        weights = {}
        for strategy_name, score in strategy_scores.items():
            # Use exponential to emphasize differences, then normalize
            exp_score = math.exp(score * 2)  # Scale factor for sensitivity
            weights[strategy_name] = exp_score
        
        # Normalize weights
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {name: weight / total_weight for name, weight in weights.items()}
        
        return weights


class EnsembleManager:
    """Main ensemble manager that combines strategies with dynamic weighting."""
    
    def __init__(
        self,
        performance_tracker: Optional[StrategyPerformanceTracker] = None,
        weight_calculator: Optional[EnsembleWeightCalculator] = None
    ):
        self.performance_tracker = performance_tracker or StrategyPerformanceTracker()
        self.weight_calculator = weight_calculator or EnsembleWeightCalculator()
    
    async def get_strategy_weights(
        self, 
        session: AsyncSession,
        user_id: Optional[str] = None
    ) -> Dict[str, float]:
        """Get current dynamic weights for all strategies."""
        # Get performance metrics for all strategies
        strategy_metrics = await self.performance_tracker.get_all_strategy_metrics(
            session, user_id
        )
        
        # Calculate weights based on performance
        weights = self.weight_calculator.calculate_weights(strategy_metrics)
        
        return weights
    
    def combine_signals(
        self, 
        signals: List[Dict[str, Any]], 
        weights: Dict[str, float]
    ) -> Dict[str, Any]:
        """Combine multiple strategy signals into a unified signal."""
        if not signals:
            return {
                "strategy": "ensemble",
                "action": "hold",
                "entry": 0.0,
                "sl": 0.0,
                "tp": 0.0,
                "confidence": 0.0,
                "timestamp": datetime.utcnow().isoformat(),
                "reason": "no_signals"
            }
        
        # Filter signals that have weights
        weighted_signals = []
        for signal in signals:
            strategy_name = signal.get("strategy", "unknown")
            if strategy_name in weights and weights[strategy_name] > 0:
                weighted_signals.append(signal)
        
        if not weighted_signals:
            return {
                "strategy": "ensemble",
                "action": "hold",
                "entry": 0.0,
                "sl": 0.0,
                "tp": 0.0,
                "confidence": 0.0,
                "timestamp": datetime.utcnow().isoformat(),
                "reason": "no_weighted_signals"
            }
        
        # Combine signals
        total_confidence = 0.0
        weighted_entry = 0.0
        weighted_sl = 0.0
        weighted_tp = 0.0
        buy_weight = 0.0
        sell_weight = 0.0
        
        for signal in weighted_signals:
            strategy_name = signal.get("strategy", "unknown")
            weight = weights.get(strategy_name, 0.0)
            confidence = signal.get("confidence", 0.0)
            action = signal.get("action", "hold")
            
            # Weighted confidence
            total_confidence += confidence * weight
            
            # Weighted price levels
            entry = signal.get("entry", 0.0)
            sl = signal.get("sl", 0.0)
            tp = signal.get("tp", 0.0)
            
            if entry > 0:
                weighted_entry += entry * weight
            if sl > 0:
                weighted_sl += sl * weight
            if tp > 0:
                weighted_tp += tp * weight
            
            # Action weighting
            if action == "buy":
                buy_weight += weight * confidence
            elif action == "sell":
                sell_weight += weight * confidence
        
        # Determine final action
        if buy_weight > sell_weight and buy_weight > 0.3:  # Minimum threshold
            final_action = "buy"
            final_confidence = buy_weight
        elif sell_weight > buy_weight and sell_weight > 0.3:
            final_action = "sell"
            final_confidence = sell_weight
        else:
            final_action = "hold"
            final_confidence = 0.0
        
        return {
            "strategy": "ensemble",
            "action": final_action,
            "entry": float(weighted_entry) if weighted_entry > 0 else 0.0,
            "sl": float(weighted_sl) if weighted_sl > 0 else 0.0,
            "tp": float(weighted_tp) if weighted_tp > 0 else 0.0,
            "confidence": float(final_confidence),
            "timestamp": datetime.utcnow().isoformat(),
            "component_signals": [
                {
                    "strategy": s.get("strategy"),
                    "action": s.get("action"),
                    "confidence": s.get("confidence"),
                    "weight": weights.get(s.get("strategy", "unknown"), 0.0)
                }
                for s in weighted_signals
            ],
            "weights": weights
        }
    
    async def get_weighted_signal(
        self, 
        session: AsyncSession,
        signals: List[Dict[str, Any]],
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get unified signal with combined confidence from multiple strategies."""
        try:
            # Get current strategy weights
            weights = await self.get_strategy_weights(session, user_id)
            
            # Combine signals
            ensemble_signal = self.combine_signals(signals, weights)
            
            return ensemble_signal
            
        except Exception as exc:
            logger.exception(f"Error generating weighted signal: {exc}")
            return {
                "strategy": "ensemble",
                "action": "hold",
                "entry": 0.0,
                "sl": 0.0,
                "tp": 0.0,
                "confidence": 0.0,
                "timestamp": datetime.utcnow().isoformat(),
                "reason": f"error: {str(exc)}"
            }


# Convenience functions for external use
async def get_ensemble_signal(
    session: AsyncSession,
    signals: List[Dict[str, Any]],
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """Get ensemble signal from multiple strategy signals."""
    manager = EnsembleManager()
    return await manager.get_weighted_signal(session, signals, user_id)


async def get_strategy_performance(
    session: AsyncSession,
    strategy_name: str,
    user_id: Optional[str] = None
) -> Dict[str, float]:
    """Get performance metrics for a specific strategy."""
    tracker = StrategyPerformanceTracker()
    return await tracker.calculate_strategy_metrics(session, strategy_name, user_id)
