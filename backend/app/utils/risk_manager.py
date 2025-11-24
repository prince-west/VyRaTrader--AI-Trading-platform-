# backend/app/utils/risk_manager.py
async def enforce_risk_limits(portfolio, trade_signal):
    """Basic risk checks before executing trades."""
    max_daily_loss = 0.03  # 3% of balance
    max_position = 0.20    # 20% of balance

    balance = getattr(portfolio, "balance", None) or portfolio.get("balance", 0)
    daily_loss = getattr(portfolio, "daily_loss", 0) or portfolio.get("daily_loss", 0)

    if balance and daily_loss and daily_loss > max_daily_loss * balance:
        return False, "daily_loss_exceeded"

    requested_amount = trade_signal.get("amount")
    if requested_amount is None:
        frac = trade_signal.get("fraction")
        if frac is not None and balance:
            requested_amount = frac * balance

    if requested_amount is not None and balance:
        if requested_amount > max_position * balance:
            return False, "position_too_large"

    return True, "ok"
