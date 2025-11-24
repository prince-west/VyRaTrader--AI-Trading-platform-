"""
Unit tests for risk manager module.
Tests position sizing calculations, risk parity allocation, and drawdown protection.
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from backend.app.services.risk_manager import (
    position_sizing,
    risk_parity_allocator,
    kelly_fraction,
    RISK_MAP,
    RiskManager,
    DrawdownProtection,
    calculate_position_size,
    allocate_strategies
)
from backend.app.db.models import Trade, Account
from backend.app.db.session import get_session


@pytest.fixture
def mock_session():
    """Mock database session for risk manager tests."""
    session = AsyncMock()
    session.exec = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def sample_strategy_signals():
    """Sample strategy signals for testing."""
    return [
        {
            'strategy': 'trend_following',
            'symbol': 'BTCUSDT',
            'action': 'buy',
            'entry': 50000.0,
            'sl': 49000.0,
            'tp': 52000.0,
            'confidence': 0.8
        },
        {
            'strategy': 'volatility_breakout',
            'symbol': 'ETHUSDT',
            'action': 'sell',
            'entry': 3000.0,
            'sl': 3100.0,
            'tp': 2800.0,
            'confidence': 0.6
        },
        {
            'strategy': 'sentiment_filter',
            'symbol': 'BTCUSDT',
            'action': 'hold',
            'entry': 0.0,
            'sl': 0.0,
            'tp': 0.0,
            'confidence': 0.4
        }
    ]


@pytest.fixture
def sample_trades():
    """Sample trades for drawdown calculation."""
    base_time = datetime.utcnow() - timedelta(days=10)
    return [
        Trade(
            id="1",
            user_id="test_user",
            strategy="trend_following",
            symbol="BTCUSDT",
            side="buy",
            size=0.1,
            price=50000.0,
            status="closed",
            profit_loss=500.0,  # Profit
            opened_at=base_time,
            closed_at=base_time + timedelta(hours=1)
        ),
        Trade(
            id="2",
            user_id="test_user",
            strategy="volatility_breakout",
            symbol="ETHUSDT",
            side="sell",
            size=1.0,
            price=3000.0,
            status="closed",
            profit_loss=-200.0,  # Loss
            opened_at=base_time + timedelta(days=1),
            closed_at=base_time + timedelta(days=1, hours=2)
        ),
        Trade(
            id="3",
            user_id="test_user",
            strategy="trend_following",
            symbol="BTCUSDT",
            side="buy",
            size=0.1,
            price=51000.0,
            status="closed",
            profit_loss=-300.0,  # Loss
            opened_at=base_time + timedelta(days=2),
            closed_at=base_time + timedelta(days=2, hours=3)
        )
    ]


class TestPositionSizing:
    """Test position sizing calculations."""
    
    def test_position_sizing_normal_case(self):
        """Test position sizing with normal parameters."""
        account_balance = 10000.0
        risk_pct = 0.02  # 2%
        stop_distance_atr = 0.01  # 1%
        volatility_scale = 1.0
        
        position_size = position_sizing(account_balance, risk_pct, stop_distance_atr, volatility_scale)
        
        # Expected: (10000 * 0.02) / 0.01 = 20000
        # But capped at 10% of account = 1000
        assert position_size == 1000.0
    
    def test_position_sizing_high_volatility(self):
        """Test position sizing with high volatility scaling."""
        account_balance = 10000.0
        risk_pct = 0.02
        stop_distance_atr = 0.01
        volatility_scale = 2.0  # High volatility
        
        position_size = position_sizing(account_balance, risk_pct, stop_distance_atr, volatility_scale)
        
        # Should be reduced by volatility scale
        assert position_size < 1000.0
        assert position_size > 0.0
    
    def test_position_sizing_edge_cases(self):
        """Test position sizing edge cases."""
        # Zero account balance
        assert position_sizing(0.0, 0.02, 0.01, 1.0) == 0.0
        
        # Zero risk percentage
        assert position_sizing(10000.0, 0.0, 0.01, 1.0) == 0.0
        
        # Zero stop distance
        assert position_sizing(10000.0, 0.02, 0.0, 1.0) == 0.0
        
        # Negative values
        assert position_sizing(-1000.0, 0.02, 0.01, 1.0) == 0.0
        assert position_sizing(10000.0, -0.02, 0.01, 1.0) == 0.0
        assert position_sizing(10000.0, 0.02, -0.01, 1.0) == 0.0
    
    def test_position_sizing_max_cap(self):
        """Test position sizing maximum cap."""
        account_balance = 10000.0
        risk_pct = 0.05  # 5%
        stop_distance_atr = 0.001  # 0.1% - very tight stop
        
        position_size = position_sizing(account_balance, risk_pct, stop_distance_atr, 1.0)
        
        # Should be capped at 10% of account (1000)
        assert position_size == 1000.0
    
    def test_calculate_position_size_convenience(self):
        """Test convenience function for position sizing."""
        result = calculate_position_size(10000.0, 0.02, 0.01, 1.0)
        assert result == 1000.0


class TestKellyFraction:
    """Test Kelly criterion calculations."""
    
    def test_kelly_fraction_positive_expectation(self):
        """Test Kelly fraction with positive expectation."""
        win_rate = 0.6  # 60% win rate
        win_loss_ratio = 2.0  # Win 2x what you lose
        
        kelly = kelly_fraction(win_rate, win_loss_ratio)
        
        # Expected: (2.0 * 0.6 - 0.4) / 2.0 = 0.4
        assert kelly == 0.4
    
    def test_kelly_fraction_negative_expectation(self):
        """Test Kelly fraction with negative expectation."""
        win_rate = 0.4  # 40% win rate
        win_loss_ratio = 1.0  # Win same as you lose
        
        kelly = kelly_fraction(win_rate, win_loss_ratio)
        
        # Expected: (1.0 * 0.4 - 0.6) / 1.0 = -0.2
        # Should return 0.0 (no position)
        assert kelly == 0.0
    
    def test_kelly_fraction_edge_cases(self):
        """Test Kelly fraction edge cases."""
        # Zero win rate
        assert kelly_fraction(0.0, 2.0) == 0.0
        
        # Zero win/loss ratio
        assert kelly_fraction(0.6, 0.0) == 0.0
        
        # Perfect win rate
        assert kelly_fraction(1.0, 2.0) == 1.0
        
        # Capped at 1.0
        assert kelly_fraction(0.9, 10.0) == 1.0


class TestRiskParityAllocator:
    """Test risk parity allocation."""
    
    def test_risk_parity_allocator_basic(self, sample_strategy_signals):
        """Test basic risk parity allocation."""
        allocations = risk_parity_allocator(sample_strategy_signals)
        
        assert isinstance(allocations, dict)
        assert len(allocations) > 0
        
        # Check that allocations sum to 1.0
        total_allocation = sum(allocations.values())
        assert abs(total_allocation - 1.0) < 0.001
        
        # Check that all allocations are positive
        for allocation in allocations.values():
            assert allocation >= 0.0
    
    def test_risk_parity_allocator_empty_signals(self):
        """Test risk parity allocation with empty signals."""
        allocations = risk_parity_allocator([])
        assert allocations == {}
    
    def test_risk_parity_allocator_single_strategy(self):
        """Test risk parity allocation with single strategy."""
        signals = [{
            'strategy': 'trend_following',
            'confidence': 0.8
        }]
        
        allocations = risk_parity_allocator(signals)
        
        assert 'trend_following' in allocations
        assert allocations['trend_following'] == 1.0
    
    def test_risk_parity_allocator_confidence_weighting(self):
        """Test that higher confidence strategies get higher allocations."""
        signals = [
            {'strategy': 'high_confidence', 'confidence': 0.9},
            {'strategy': 'low_confidence', 'confidence': 0.3}
        ]
        
        allocations = risk_parity_allocator(signals)
        
        assert allocations['high_confidence'] > allocations['low_confidence']
    
    def test_allocate_strategies_convenience(self, sample_strategy_signals):
        """Test convenience function for strategy allocation."""
        allocations = allocate_strategies(sample_strategy_signals)
        
        assert isinstance(allocations, dict)
        assert len(allocations) > 0


class TestRiskManager:
    """Test main risk manager class."""
    
    def test_risk_manager_initialization(self):
        """Test risk manager initialization."""
        risk_manager = RiskManager()
        assert risk_manager.drawdown_protection is not None
        
        # Test with custom drawdown protection
        custom_dd = DrawdownProtection(max_drawdown_pct=0.1)
        risk_manager = RiskManager(custom_dd)
        assert risk_manager.drawdown_protection == custom_dd
    
    def test_apply_risk_management_low_risk(self):
        """Test risk management application with low risk profile."""
        risk_manager = RiskManager()
        
        ensemble_decision = {
            'signal': 'buy',
            'size': 0.2  # 20% suggested
        }
        
        result = risk_manager.apply(ensemble_decision, 10000.0, "Low")
        
        assert 'position_size' in result
        assert 'risk_params' in result
        assert result['risk_params'] == RISK_MAP["Low"]
        
        # Should be reduced by risk multiplier (0.3) and capped by max_vol_alloc (0.10)
        expected_size = 10000.0 * min(0.2 * 0.3, 0.10)
        assert result['position_size'] == expected_size
    
    def test_apply_risk_management_high_risk(self):
        """Test risk management application with high risk profile."""
        risk_manager = RiskManager()
        
        ensemble_decision = {
            'signal': 'buy',
            'size': 0.5  # 50% suggested
        }
        
        result = risk_manager.apply(ensemble_decision, 10000.0, "High")
        
        # Should be reduced by risk multiplier (1.0) and capped by max_vol_alloc (0.60)
        expected_size = 10000.0 * min(0.5 * 1.0, 0.60)
        assert result['position_size'] == expected_size
    
    def test_apply_risk_management_unknown_risk(self):
        """Test risk management with unknown risk profile."""
        risk_manager = RiskManager()
        
        ensemble_decision = {
            'signal': 'buy',
            'size': 0.2
        }
        
        result = risk_manager.apply(ensemble_decision, 10000.0, "Unknown")
        
        # Should default to Medium risk
        assert result['risk_params'] == RISK_MAP["Medium"]
    
    @pytest.mark.asyncio
    async def test_apply_comprehensive_risk_management(self, mock_session, sample_strategy_signals, sample_trades):
        """Test comprehensive risk management."""
        # Mock account
        mock_account = Account(
            id="test_account",
            user_id="test_user",
            currency="USD",
            available_balance=10000.0,
            ledger_balance=10000.0
        )
        
        # Mock database queries
        mock_session.exec.return_value.first.return_value = mock_account
        mock_session.exec.return_value.all.return_value = sample_trades
        
        with patch('backend.app.services.risk_manager.get_session') as mock_get_session:
            mock_get_session.return_value.__aiter__.return_value = [mock_session]
            
            risk_manager = RiskManager()
            result = await risk_manager.apply_comprehensive_risk_management(
                mock_session, sample_strategy_signals, "test_user", 10000.0, "Medium"
            )
            
            assert 'signals' in result
            assert 'allocations' in result
            assert 'kill_switch_info' in result
            assert 'total_allocated' in result
            
            # Check that signals have position sizes
            for signal in result['signals']:
                assert 'position_size' in signal
                assert signal['position_size'] >= 0.0
            
            # Check allocations
            assert isinstance(result['allocations'], dict)
            assert 0.0 <= result['total_allocated'] <= 1.0


class TestDrawdownProtection:
    """Test drawdown protection functionality."""
    
    def test_drawdown_protection_initialization(self):
        """Test drawdown protection initialization."""
        dd_protection = DrawdownProtection()
        assert dd_protection.max_drawdown_pct == 0.15
        assert dd_protection.lookback_days == 30
        assert dd_protection.reduction_factor == 0.5
        assert dd_protection.kill_switch_active == False
        
        # Test custom parameters
        dd_protection = DrawdownProtection(
            max_drawdown_pct=0.1,
            lookback_days=14,
            reduction_factor=0.3
        )
        assert dd_protection.max_drawdown_pct == 0.1
        assert dd_protection.lookback_days == 14
        assert dd_protection.reduction_factor == 0.3
    
    @pytest.mark.asyncio
    async def test_calculate_drawdown_no_account(self, mock_session):
        """Test drawdown calculation with no account."""
        mock_session.exec.return_value.first.return_value = None
        
        dd_protection = DrawdownProtection()
        result = await dd_protection.calculate_drawdown(mock_session, "nonexistent_user")
        
        assert result['current_drawdown'] == 0.0
        assert result['peak_balance'] == 0.0
        assert result['current_balance'] == 0.0
    
    @pytest.mark.asyncio
    async def test_calculate_drawdown_no_trades(self, mock_session):
        """Test drawdown calculation with no trades."""
        mock_account = Account(
            id="test_account",
            user_id="test_user",
            available_balance=10000.0,
            ledger_balance=10000.0
        )
        
        mock_session.exec.return_value.first.return_value = mock_account
        mock_session.exec.return_value.all.return_value = []
        
        dd_protection = DrawdownProtection()
        result = await dd_protection.calculate_drawdown(mock_session, "test_user")
        
        assert result['current_drawdown'] == 0.0
        assert result['peak_balance'] == 10000.0
        assert result['current_balance'] == 10000.0
    
    @pytest.mark.asyncio
    async def test_calculate_drawdown_with_trades(self, mock_session, sample_trades):
        """Test drawdown calculation with trades."""
        mock_account = Account(
            id="test_account",
            user_id="test_user",
            available_balance=10000.0,  # Current balance
            ledger_balance=10000.0
        )
        
        mock_session.exec.return_value.first.return_value = mock_account
        mock_session.exec.return_value.all.return_value = sample_trades
        
        dd_protection = DrawdownProtection()
        result = await dd_protection.calculate_drawdown(mock_session, "test_user")
        
        assert 'current_drawdown' in result
        assert 'peak_balance' in result
        assert 'current_balance' in result
        assert result['current_balance'] == 10000.0
        assert result['peak_balance'] >= result['current_balance']
        assert 0.0 <= result['current_drawdown'] <= 1.0
    
    @pytest.mark.asyncio
    async def test_check_kill_switch_below_threshold(self, mock_session, sample_trades):
        """Test kill switch check when drawdown is below threshold."""
        mock_account = Account(
            id="test_account",
            user_id="test_user",
            available_balance=10000.0,
            ledger_balance=10000.0
        )
        
        mock_session.exec.return_value.first.return_value = mock_account
        mock_session.exec.return_value.all.return_value = sample_trades
        
        dd_protection = DrawdownProtection(max_drawdown_pct=0.5)  # High threshold
        result = await dd_protection.check_kill_switch(mock_session, "test_user")
        
        assert result['kill_switch_active'] == False
        assert 'current_drawdown' in result
        assert 'max_drawdown' in result
    
    @pytest.mark.asyncio
    async def test_check_kill_switch_above_threshold(self, mock_session):
        """Test kill switch check when drawdown is above threshold."""
        # Create trades that result in high drawdown
        high_drawdown_trades = [
            Trade(
                id="1",
                user_id="test_user",
                strategy="test",
                symbol="BTCUSDT",
                side="buy",
                size=0.1,
                price=50000.0,
                status="closed",
                profit_loss=-2000.0,  # Large loss
                opened_at=datetime.utcnow() - timedelta(days=1),
                closed_at=datetime.utcnow() - timedelta(days=1, hours=1)
            )
        ]
        
        mock_account = Account(
            id="test_account",
            user_id="test_user",
            available_balance=8000.0,  # Reduced balance
            ledger_balance=8000.0
        )
        
        mock_session.exec.return_value.first.return_value = mock_account
        mock_session.exec.return_value.all.return_value = high_drawdown_trades
        
        dd_protection = DrawdownProtection(max_drawdown_pct=0.1)  # Low threshold
        result = await dd_protection.check_kill_switch(mock_session, "test_user")
        
        # Should activate kill switch if drawdown > 10%
        assert result['kill_switch_active'] == True
        assert result['current_drawdown'] > 0.1
    
    def test_apply_drawdown_protection_inactive(self):
        """Test drawdown protection when kill switch is inactive."""
        dd_protection = DrawdownProtection()
        dd_protection.kill_switch_active = False
        
        allocations = {'strategy1': 0.6, 'strategy2': 0.4}
        protected = dd_protection.apply_drawdown_protection(allocations)
        
        # Should return original allocations
        assert protected == allocations
    
    def test_apply_drawdown_protection_active(self):
        """Test drawdown protection when kill switch is active."""
        dd_protection = DrawdownProtection(reduction_factor=0.5)
        dd_protection.kill_switch_active = True
        
        allocations = {'strategy1': 0.6, 'strategy2': 0.4}
        protected = dd_protection.apply_drawdown_protection(allocations)
        
        # Should reduce allocations by reduction factor
        assert protected['strategy1'] == 0.3
        assert protected['strategy2'] == 0.2
    
    def test_reset_kill_switch(self):
        """Test kill switch reset."""
        dd_protection = DrawdownProtection()
        dd_protection.kill_switch_active = True
        
        dd_protection.reset_kill_switch()
        
        assert dd_protection.kill_switch_active == False


@pytest.mark.integration
class TestRiskManagerIntegration:
    """Integration tests for risk manager."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_risk_management(self, mock_session, sample_strategy_signals):
        """Test end-to-end risk management process."""
        # Mock account and trades
        mock_account = Account(
            id="test_account",
            user_id="test_user",
            available_balance=10000.0,
            ledger_balance=10000.0
        )
        
        mock_session.exec.return_value.first.return_value = mock_account
        mock_session.exec.return_value.all.return_value = []
        
        with patch('backend.app.services.risk_manager.get_session') as mock_get_session:
            mock_get_session.return_value.__aiter__.return_value = [mock_session]
            
            risk_manager = RiskManager()
            result = await risk_manager.apply_comprehensive_risk_management(
                mock_session, sample_strategy_signals, "test_user", 10000.0, "Medium"
            )
            
            # Verify complete result structure
            assert 'signals' in result
            assert 'allocations' in result
            assert 'kill_switch_info' in result
            assert 'total_allocated' in result
            
            # Verify signal processing
            assert len(result['signals']) > 0
            for signal in result['signals']:
                assert 'position_size' in signal
                assert signal['position_size'] >= 0.0
            
            # Verify allocations
            assert isinstance(result['allocations'], dict)
            assert len(result['allocations']) > 0
            assert 0.0 <= result['total_allocated'] <= 1.0
            
            # Verify kill switch info
            assert 'kill_switch_active' in result['kill_switch_info']
            assert 'current_drawdown' in result['kill_switch_info']
    
    def test_risk_map_consistency(self):
        """Test that risk map has consistent structure."""
        for risk_level, params in RISK_MAP.items():
            assert 'risk_multiplier' in params
            assert 'max_vol_alloc' in params
            assert 'stop_loss_pct' in params
            
            assert 0.0 <= params['risk_multiplier'] <= 2.0
            assert 0.0 <= params['max_vol_alloc'] <= 1.0
            assert 0.0 <= params['stop_loss_pct'] <= 1.0
    
    @pytest.mark.asyncio
    async def test_error_handling(self, mock_session):
        """Test error handling in risk management."""
        # Mock database error
        mock_session.exec.side_effect = Exception("Database error")
        
        risk_manager = RiskManager()
        
        # Should handle errors gracefully
        try:
            await risk_manager.apply_comprehensive_risk_management(
                mock_session, [], "test_user", 10000.0, "Medium"
            )
        except Exception as exc:
            pytest.fail(f"Risk manager should handle errors gracefully: {exc}")
