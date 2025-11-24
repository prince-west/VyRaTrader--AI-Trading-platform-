import pytest
import numpy as np
import pandas as pd
from app.ai.rl_agent import PortfolioEnv, RLAgent

def test_portfolio_env():
    prices = pd.Series([100, 101, 99, 102])
    env = PortfolioEnv(prices)
    
    obs = env.reset()
    assert obs.shape == (10,)
    
    obs, reward, done, info = env.step(2)  # buy
    assert not done
    assert isinstance(reward, float)
    assert env.position == 1

def test_rl_agent_predict():
    agent = RLAgent()
    obs = np.zeros(10)
    action = agent.predict(obs)
    assert action in (0, 1, 2)
