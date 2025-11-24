# backend/app/services/risk_meter.py
"""
Risk meter mapping as in the spec: Low/Medium/High -> numeric risk_factor and attributes.
"""
def get_risk_profile(risk_level: str):
    r = risk_level.capitalize()
    if r == "Low":
        return {
            "risk_level": "Low",
            "risk_multiplier": 0.3,
            "expected_monthly_return": "0.5-2%",
            "max_volatile_allocation_pct": 10,
            "stop_loss_pct": "2-3"
        }
    if r == "High":
        return {
            "risk_level": "High",
            "risk_multiplier": 1.0,
            "expected_monthly_return": "5%+",
            "max_volatile_allocation_pct": 60,
            "stop_loss_pct": "10-20"
        }
    # Default Medium
    return {
        "risk_level": "Medium",
        "risk_multiplier": 0.6,
        "expected_monthly_return": "2-4%",
        "max_volatile_allocation_pct": 25,
        "stop_loss_pct": "5-8"
    }
