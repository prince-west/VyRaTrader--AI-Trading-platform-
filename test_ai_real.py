"""
Test script to verify AI is actually working and returning real responses.
This will show you EXACTLY what the AI returns - no deception.
"""

import os
import httpx
import json
from dotenv import load_dotenv

load_dotenv()

def test_groq_ai():
    """Test Groq API with a real signal to see actual response."""
    api_key = os.getenv("GROQ_API_KEY")
    model = os.getenv("AI_MODEL", "llama-3.1-8b-instant")
    
    if not api_key:
        print("ERROR: GROQ_API_KEY not found in .env")
        return False
    
    print("=" * 60)
    print("TESTING GROQ AI - REAL API CALL")
    print("=" * 60)
    print(f"API Key: {api_key[:10]}...{api_key[-4:]}")
    print(f"Model: {model}")
    print()
    
    # Create a test signal prompt (same format as your system uses)
    test_prompt = """
You are a veteran trading analyst with 15 years of experience. You REJECT 70% of signals as inadequate.

A junior trader presents this signal:

ASSET: BTCUSDT
STRATEGY: momentum (Weight: 1.1x)
ACTION: BUY
ENTRY: $65000.00
STOP LOSS: $64000.00
TAKE PROFIT: $67000.00
RISK/REWARD: 2.0:1
STRATEGY CONFIDENCE: 0.90/1.0

ENSEMBLE ANALYSIS:
- Weighted Consensus Score: 0.99 (≥2.0 is strong)
- Consensus Count: 0 strategies agree
- Pre-AI Score: 1/5 confirmations

TECHNICAL INDICATORS:
RSI: 45.0 (NEUTRAL)
MACD: 0.1234 vs Signal: 0.1000 (BULLISH)
Histogram: 0.0234 (WEAK)
Volume: 1.20x average (NORMAL)
Volatility: 1.50% (NORMAL)

REASONING: MACD crossover detected
PRE-CHECKS PASSED: No-conflict

Current Market Context:
PRICE TRENDS (to help identify if user executes late):
Current Price: 65,000.0000
Price 1h ago: 64,800.0000 (+0.31%) - Trend: BULLISH
Price 24h ago: 64,500.0000 (+0.78%) - Trend: BULLISH

⚠️ IMPORTANT: If price has moved significantly since signal, the user may be executing late.
⚠️ Consider warning if price moved >2% in the wrong direction (e.g., buy signal but price fell 3%).

Market Status: Market is open

CRITICAL EVALUATION REQUIRED (Based on Research-Proven Methods):

REJECT (score <7) if:
- Setup is premature or incomplete
- Risk/reward is suboptimal (<2:1)
- Market conditions are unfavorable
- Technical levels are unclear
- Multiple confirmations missing (<3/5)
- Pattern not fully completed
- Weighted consensus <2.0 AND single strategy confidence <0.70
- No divergence detected (for RSI/MACD strategies)
- Volume confirmation missing (for breakout strategies)

APPROVE (score ≥7) ONLY if:
- Crystal clear technical setup
- Strong risk/reward (≥2:1 confirmed)
- Multiple solid confirmations (≥3/5)
- High probability based on market structure
- Weighted consensus ≥2.0 OR very high confidence (≥0.75) from high-weight strategy
- Divergence detected (if applicable) - this is a STRONG signal
- Volume confirmation present (if required)
- You would personally take this trade

Respond in this EXACT format:

VERDICT: [APPROVE or REJECT]
CONFIDENCE: [1-10]
STRENGTHS: [2-3 specific positives]
CONCERNS: [2-3 specific risks]
RECOMMENDATION: [One clear sentence: take trade or skip]

Be brutally honest. Most signals should be rejected. Only approve high-probability setups.
"""
    
    print("Sending request to Groq API...")
    print()
    
    try:
        response = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a trading signal analyst. Analyze signals and rate confidence 1-10."},
                    {"role": "user", "content": test_prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 500,
            },
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        
        print(f"HTTP Status: {response.status_code}")
        print()
        
        if response.status_code != 200:
            print(f"ERROR: API returned status {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        data = response.json()
        ai_response = data["choices"][0]["message"]["content"]
        
        print("=" * 60)
        print("ACTUAL AI RESPONSE (NO FAKE DATA):")
        print("=" * 60)
        print(ai_response)
        print()
        print("=" * 60)
        print("RAW API RESPONSE (JSON):")
        print("=" * 60)
        print(json.dumps(data, indent=2))
        print()
        
        # Try to extract confidence
        import re
        confidence_match = re.search(r'CONFIDENCE:\s*(\d+(?:\.\d+)?)', ai_response, re.IGNORECASE)
        if confidence_match:
            confidence = float(confidence_match.group(1))
            print(f"Extracted Confidence: {confidence}/10")
        else:
            print("WARNING: Could not extract confidence from response")
        
        verdict_match = re.search(r'VERDICT:\s*(APPROVE|REJECT)', ai_response, re.IGNORECASE)
        if verdict_match:
            verdict = verdict_match.group(1)
            print(f"Extracted Verdict: {verdict}")
        else:
            print("WARNING: Could not extract verdict from response")
        
        print()
        print("=" * 60)
        print("CONCLUSION:")
        print("=" * 60)
        print("[OK] AI is working - this is a REAL response from Groq API")
        print("[OK] No fake/mock data - this came directly from the AI model")
        print("[OK] Response is unique and based on the signal you sent")
        
        return True
        
    except httpx.TimeoutException:
        print("ERROR: Request timed out after 30 seconds")
        print("This means the AI is NOT responding in time")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_groq_ai()

