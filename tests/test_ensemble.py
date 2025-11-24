import pytest
import numpy as np
import pandas as pd
from app.ai.ensemble_core import EnsembleCore

def test_ensemble_signals():
    ensemble = EnsembleCore()
    signals = ensemble.collect_signals("BTC-USD")
    assert isinstance(signals, dict)
    
    signal = ensemble.generate_final_signal("BTC-USD")
    assert signal in ("buy", "sell", "hold")

def test_empty_signals_return_hold():
    ensemble = EnsembleCore()
    assert ensemble.generate_final_signal("INVALID") == "hold"
