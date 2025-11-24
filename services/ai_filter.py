"""
AI Signal Filter Service
Filters trading signals using local AI (Ollama) or fallback providers (Groq/HuggingFace).

Primary: Ollama (local, free)
Fallback: Groq or HuggingFace (free tier)
"""

import json
import re
import time
from typing import Dict, Any, Optional
from collections import deque
from datetime import datetime, timedelta
import httpx
import sys
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.logger import logger

# Import market hours utility
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from services.market_hours import MarketHours
except ImportError:
    # Fallback if market_hours not available
    class MarketHours:
        @staticmethod
        def is_symbol_market_open(symbol: str) -> bool:
            return True  # Default to always open
        @staticmethod
        def get_market_status_message() -> str:
            return "Market hours check unavailable"


class AIFilter:
    """
    AI filter that analyzes trading signals and rates confidence.
    Only signals with AI confidence >= threshold are approved.
    """
    
    def __init__(
        self,
        provider: str = "ollama",
        model: str = "llama3.1",
        confidence_threshold: float = 7.0,
        groq_api_key: Optional[str] = None,
        huggingface_api_key: Optional[str] = None,
    ):
        """
        Initialize AI filter.
        
        Args:
            provider: "ollama", "groq", or "huggingface"
            model: Model name (e.g., "llama3.1", "llama-3.1-8b-8192")
            confidence_threshold: Minimum confidence score (1-10) to approve signal
            groq_api_key: API key for Groq (if using groq provider)
            huggingface_api_key: API key for HuggingFace (if using huggingface provider)
        """
        self.provider = provider.lower()
        self.model = model
        self.confidence_threshold = confidence_threshold
        self.groq_api_key = groq_api_key
        self.huggingface_api_key = huggingface_api_key
        
        # Rate limiting for Groq (30 requests/minute free tier)
        self.groq_rate_limit = 30  # requests per minute
        self.groq_request_times = deque(maxlen=self.groq_rate_limit)  # Track request times
        
        logger.info(f"AI Filter initialized: provider={provider}, model={model}, threshold={confidence_threshold}")
        if self.provider == "groq":
            logger.info(f"   - Groq rate limiting: {self.groq_rate_limit} requests/minute")
        
        # Test connection on startup
        if self.provider == "ollama":
            self._test_ollama()
    
    def _test_ollama(self) -> bool:
        """Test if Ollama is running and accessible."""
        try:
            response = httpx.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                logger.info("✅ Ollama connection successful")
                return True
            else:
                logger.warning(f"⚠️  Ollama responded with status {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Cannot connect to Ollama: {e}")
            logger.error("   Make sure Ollama is running: ollama serve")
            logger.error("   And model is pulled: ollama pull llama3.1")
            return False
    
    def _ask_ollama(self, prompt: str) -> str:
        """
        Query Ollama for AI analysis.
        Returns the AI's response text.
        """
        # Try with longer timeout and retry logic
        max_retries = 2
        timeout_seconds = 60  # Increased from 30 to 60 seconds
        
        for attempt in range(max_retries):
            try:
                response = httpx.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,  # Lower temperature for more consistent responses
                            "top_p": 0.9,
                        }
                    },
                    timeout=timeout_seconds,
                )
                response.raise_for_status()
                data = response.json()
                response_text = data.get("response", "")
                if response_text:
                    return response_text
                # If response is empty, retry
                if attempt < max_retries - 1:
                    logger.debug(f"Ollama returned empty response, retrying ({attempt + 1}/{max_retries})...")
                    continue
                return ""
            except httpx.TimeoutException:
                if attempt < max_retries - 1:
                    logger.debug(f"Ollama request timed out ({timeout_seconds}s), retrying ({attempt + 1}/{max_retries})...")
                    timeout_seconds = timeout_seconds // 2  # Reduce timeout for retry
                    continue
                logger.warning(f"Ollama request timed out after {max_retries} attempts - will use fallback confidence")
                return ""  # Empty response triggers fallback mechanism
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.debug(f"Ollama request failed: {e}, retrying ({attempt + 1}/{max_retries})...")
                    continue
                logger.error(f"Ollama request failed after {max_retries} attempts: {e}")
                return ""
    
    def _wait_for_groq_rate_limit(self) -> None:
        """
        Rate limiting for Groq API (30 requests/minute free tier).
        Waits if necessary to stay under the limit.
        """
        now = time.time()
        
        # Remove requests older than 1 minute
        while self.groq_request_times and now - self.groq_request_times[0] > 60:
            self.groq_request_times.popleft()
        
        # If we've hit the limit, wait until oldest request expires
        if len(self.groq_request_times) >= self.groq_rate_limit:
            wait_time = 60 - (now - self.groq_request_times[0]) + 1  # +1 second buffer
            if wait_time > 0:
                logger.debug(f"Groq rate limit reached ({self.groq_rate_limit}/min), waiting {wait_time:.1f} seconds...")
                time.sleep(wait_time)
                # Clean up again after waiting
                now = time.time()
                while self.groq_request_times and now - self.groq_request_times[0] > 60:
                    self.groq_request_times.popleft()
        
        # Record this request time
        self.groq_request_times.append(time.time())
    
    def _ask_groq(self, prompt: str) -> str:
        """
        Query Groq API for AI analysis.
        Returns the AI's response text.
        Includes automatic rate limiting to stay under free tier limits.
        """
        if not self.groq_api_key:
            logger.error("Groq API key not provided")
            logger.error("   Get free API key from: https://console.groq.com/")
            logger.error("   Add to .env: GROQ_API_KEY=your_key_here")
            return ""
        
        # Rate limiting: ensure we stay under 30 requests/minute
        self._wait_for_groq_rate_limit()
        
        logger.info(f"Calling Groq API with model: {self.model or 'llama-3.1-8b-instant'}")
        try:
            # Use longer timeout to prevent premature failures
            response = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                json={
                    "model": self.model or "llama-3.1-8b-instant",
                    "messages": [
                        {"role": "system", "content": "You are a trading signal analyst. Analyze signals and rate confidence 1-10."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 500,
                },
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json",
                },
                timeout=60.0,  # Increased from 30 to 60 seconds
            )
            response.raise_for_status()
            data = response.json()
            
            # Validate response structure
            if "choices" not in data or len(data["choices"]) == 0:
                logger.error(f"Groq API returned invalid response structure: {data}")
                return ""
            
            ai_response = data["choices"][0]["message"]["content"]
            
            if not ai_response or len(ai_response.strip()) == 0:
                logger.error("Groq API returned empty response content!")
                return ""
            
            logger.info(f"Groq API SUCCESS - response length: {len(ai_response)} chars")
            return ai_response
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                # Rate limit exceeded - wait and retry once
                logger.warning("Groq rate limit exceeded (429), waiting 60 seconds...")
                time.sleep(60)
                # Try one more time
                try:
                    response = httpx.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        json={
                            "model": self.model or "llama-3.1-8b-8192",
                            "messages": [
                                {"role": "system", "content": "You are a trading signal analyst. Analyze signals and rate confidence 1-10."},
                                {"role": "user", "content": prompt}
                            ],
                            "temperature": 0.3,
                            "max_tokens": 500,  # Limit response length for faster processing
                        },
                        headers={
                            "Authorization": f"Bearer {self.groq_api_key}",
                            "Content-Type": "application/json",
                        },
                        timeout=60.0,  # Increased from 30 to 60 seconds
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    if "choices" not in data or len(data["choices"]) == 0:
                        logger.error(f"Groq API retry returned invalid response: {data}")
                        return ""
                    
                    ai_response = data["choices"][0]["message"]["content"]
                    
                    if not ai_response or len(ai_response.strip()) == 0:
                        logger.error("Groq API retry returned empty response content!")
                        return ""
                    
                    logger.info(f"Groq API retry SUCCESS - response length: {len(ai_response)} chars")
                    return ai_response
                except Exception as retry_e:
                    logger.error(f"Groq API retry failed: {retry_e}")
                    return ""
            else:
                logger.error(f"Groq API request failed with HTTP {e.response.status_code}: {e}")
                logger.error(f"Response body: {e.response.text[:500]}")
                return ""
        except httpx.TimeoutException as e:
            logger.error(f"Groq API request TIMED OUT after 30 seconds: {e}")
            return ""
        except Exception as e:
            logger.error(f"Groq API request failed: {e}")
            import traceback
            logger.error(f"Full error traceback: {traceback.format_exc()}")
            return ""
    
    def _ask_huggingface(self, prompt: str) -> str:
        """
        Query HuggingFace Inference API for AI analysis.
        Returns the AI's response text.
        """
        if not self.huggingface_api_key:
            logger.error("HuggingFace API key not provided")
            return ""
        
        try:
            response = httpx.post(
                f"https://api-inference.huggingface.co/models/meta-llama/{self.model}",
                json={"inputs": prompt},
                headers={
                    "Authorization": f"Bearer {self.huggingface_api_key}",
                    "Content-Type": "application/json",
                },
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            
            # HuggingFace returns different formats, extract text
            if isinstance(data, list) and len(data) > 0:
                if isinstance(data[0], dict) and "generated_text" in data[0]:
                    return data[0]["generated_text"]
                elif isinstance(data[0], str):
                    return data[0]
            
            return json.dumps(data)
        except Exception as e:
            logger.error(f"HuggingFace API request failed: {e}")
            return ""
    
    def filter_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter a trading signal through AI analysis.
        
        Args:
            signal: Signal dict with keys: strategy, symbol, action, entry, sl, tp, confidence, timestamp
        
        Returns:
            Dict with keys:
            - approved: bool (True if AI confidence >= threshold)
            - ai_confidence: float (AI's confidence rating 1-10)
            - ai_reasoning: str (AI's explanation)
        """
        # Check if market is open for this symbol
        symbol = signal.get('symbol', 'unknown')
        market_open = MarketHours.is_symbol_market_open(symbol)
        market_status = MarketHours.get_market_status_message()
        
        # Extract price trends if available
        price_trends = signal.get('price_trends', {})
        price_trend_info = ""
        if price_trends:
            trend_1h = price_trends.get('trend_1h', 'unknown')
            trend_24h = price_trends.get('trend_24h', 'unknown')
            change_1h = price_trends.get('change_1h_pct', 0.0)
            change_24h = price_trends.get('change_24h_pct', 0.0)
            price_1h_ago = price_trends.get('price_1h_ago', signal.get('entry', 0.0))
            price_24h_ago = price_trends.get('price_24h_ago', signal.get('entry', 0.0))
            
            price_trend_info = f"""
PRICE TRENDS (to help identify if user executes late):
Current Price: {signal.get('entry', 0.0):,.4f}
Price 1h ago: {price_1h_ago:,.4f} ({'+' if change_1h >= 0 else ''}{change_1h:.2f}%) - Trend: {trend_1h.upper()}
Price 24h ago: {price_24h_ago:,.4f} ({'+' if change_24h >= 0 else ''}{change_24h:.2f}%) - Trend: {trend_24h.upper()}

⚠️ IMPORTANT: If price has moved significantly since signal, the user may be executing late.
⚠️ Consider warning if price moved >2% in the wrong direction (e.g., buy signal but price fell 3%).
"""

        # Format signal details for AI prompt
        # Calculate risk/reward ratio
        entry = signal.get('entry', 0.0)
        stop_loss = signal.get('stop_loss', signal.get('sl', 0.0))
        take_profit = signal.get('take_profit', signal.get('tp', 0.0))
        action = signal.get('action', 'unknown')
        
        if action == "buy" and entry > 0 and stop_loss > 0 and take_profit > 0:
            risk = entry - stop_loss
            reward = take_profit - entry
            rr_ratio = reward / risk if risk > 0 else 0.0
        elif action == "sell" and entry > 0 and stop_loss > 0 and take_profit > 0:
            risk = stop_loss - entry
            reward = entry - take_profit
            rr_ratio = reward / risk if risk > 0 else 0.0
        else:
            rr_ratio = 0.0
        
        # Get confirmations and pre-AI score
        confirmations = signal.get('confirmations', [])
        pre_ai_score = signal.get('pre_ai_score', len(confirmations))
        
        # Enhanced feature engineering - extract all technical indicators
        rsi = signal.get('rsi')
        macd = signal.get('macd')
        signal_line = signal.get('signal_line')
        histogram = signal.get('histogram')
        volume_ratio = signal.get('volume_ratio', 0.0)
        divergence = signal.get('divergence')
        volatility = signal.get('volatility', 0.0)
        weighted_consensus = signal.get('_reliability_info', {}).get('weighted_consensus_score', 0.0)
        strategy_weight = signal.get('_reliability_info', {}).get('strategy_weight', 1.0)
        consensus_count = signal.get('_reliability_info', {}).get('consensus_count', 0)
        
        # Build technical indicators section
        technical_indicators = []
        if rsi is not None:
            rsi_status = "OVERSOLD" if rsi < 30 else "OVERBOUGHT" if rsi > 70 else "NEUTRAL"
            technical_indicators.append(f"RSI: {rsi:.1f} ({rsi_status})")
        if macd is not None and signal_line is not None:
            macd_signal = "BULLISH" if macd > signal_line else "BEARISH"
            technical_indicators.append(f"MACD: {macd:.4f} vs Signal: {signal_line:.4f} ({macd_signal})")
        if histogram is not None:
            hist_signal = "EXPANDING" if abs(histogram) > 0.3 else "WEAK"
            technical_indicators.append(f"Histogram: {histogram:.4f} ({hist_signal})")
        if divergence:
            technical_indicators.append(f"DIVERGENCE DETECTED: {divergence.upper()} (STRONG SIGNAL)")
        if volume_ratio > 0:
            vol_status = "HIGH" if volume_ratio > 1.5 else "NORMAL" if volume_ratio > 1.0 else "LOW"
            technical_indicators.append(f"Volume: {volume_ratio:.2f}x average ({vol_status})")
        if volatility > 0:
            vol_level = "HIGH" if volatility > 0.02 else "NORMAL" if volatility > 0.01 else "LOW"
            technical_indicators.append(f"Volatility: {volatility*100:.2f}% ({vol_level})")
        
        technical_info = "\n".join(technical_indicators) if technical_indicators else "No technical indicators available"
        
        # Enhanced signal text with all features
        signal_text = f"""
You are a veteran trading analyst with 15 years of experience. You REJECT 70% of signals as inadequate.

A junior trader presents this signal:

ASSET: {signal.get('symbol', 'unknown')}
STRATEGY: {signal.get('strategy', 'unknown')} (Weight: {strategy_weight:.1f}x)
ACTION: {signal.get('action', 'unknown').upper()}
ENTRY: ${entry:.2f}
STOP LOSS: ${stop_loss:.2f}
TAKE PROFIT: ${take_profit:.2f}
RISK/REWARD: {rr_ratio:.2f}:1
STRATEGY CONFIDENCE: {signal.get('confidence', 0.0):.2f}/1.0

ENSEMBLE ANALYSIS:
- Weighted Consensus Score: {weighted_consensus:.2f} (≥2.0 is strong)
- Consensus Count: {consensus_count} strategies agree
- Pre-AI Score: {pre_ai_score}/5 confirmations

TECHNICAL INDICATORS:
{technical_info}

REASONING: {signal.get('reasoning', 'No reasoning provided')}
PRE-CHECKS PASSED: {', '.join(confirmations) if confirmations else 'None'}

Current Market Context:
{price_trend_info}
{market_status}

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

APPROVE (score ≥7) if:
- Strong risk/reward (≥2:1) AND high strategy confidence (≥0.75) - these are the MOST IMPORTANT factors
- Good technical setup (MACD crossover, momentum shift, etc.)
- Multiple confirmations (≥2/5) OR very high confidence (≥0.85) from strategy
- Weighted consensus ≥2.0 OR very high confidence (≥0.75) from high-weight strategy

GIVE HIGHER SCORES (7-8) for signals with:
- Excellent R:R (≥3:1) = +1 point
- Very high strategy confidence (≥0.85) = +1 point
- Good technical setup (MACD crossover, momentum) = +0.5 point
- Multiple confirmations (≥3/5) = +0.5 point

GIVE LOWER SCORES (4-6) for signals with:
- Neutral RSI (45-55) = -0.5 point (but don't reject if other factors are strong)
- Low volume (<1.2x) = -0.5 point
- Single strategy (no consensus) = -0.5 point

Respond in this EXACT format:

VERDICT: [APPROVE or REJECT]
CONFIDENCE: [1-10]
STRENGTHS: [2-3 specific positives]
CONCERNS: [2-3 specific risks]
RECOMMENDATION: [One clear sentence: take trade or skip]

Be balanced. Approve signals with strong R:R (≥3:1) and high confidence (≥0.75) even if RSI is neutral or volume is moderate.
"""
        
        # Query AI
        logger.info(f"Querying AI (provider: {self.provider}, model: {self.model})...")
        response = ""
        if self.provider == "ollama":
            response = self._ask_ollama(signal_text)
        elif self.provider == "groq":
            response = self._ask_groq(signal_text)
        elif self.provider == "huggingface":
            response = self._ask_huggingface(signal_text)
        else:
            logger.error(f"Unknown AI provider: {self.provider}")
            return {
                "approved": False,
                "ai_confidence": 0.0,
                "ai_reasoning": f"Unknown provider: {self.provider}",
            }
        
        logger.info(f"AI response status: {'SUCCESS' if response else 'EMPTY/TIMEOUT - using fallback'}")
        
        if not response:
            logger.warning(f"AI returned empty response (timeout/unavailable) - using intelligent fallback. Provider: {self.provider}, Model: {self.model}")
            # Fallback: Use strategy confidence when AI is unavailable
            # BUT: Give better scores for highly reliable signals (consensus or very high confidence)
            # IMPORTANT: Never approve if market is closed
            strategy_confidence = signal.get('confidence', 0.0)
            reliability_info = signal.get('_reliability_info', {})  # Passed from signal generator
            consensus_count = reliability_info.get('consensus_count', 0)
            is_highly_reliable = reliability_info.get('is_reliable', False)
            
            if strategy_confidence > 0.0:
                # Base mapping: strategy confidence to AI confidence (1-10 scale)
                base_ai_confidence = 2.0 + (strategy_confidence * 4.5)  # Scales 0.0-1.0 to 2.0-6.5
                
                # BONUS for highly reliable signals when AI times out:
                # If signal has consensus (2+ strategies) OR very high confidence (>=0.75),
                # give it a boost because reliability check already validated it
                ai_confidence = base_ai_confidence
                
                if is_highly_reliable:
                    # Give bonus: +2.0 for consensus signals, +1.5 for high confidence
                    if consensus_count >= 2:
                        # Multiple strategies agree - very reliable, give good score
                        ai_confidence = min(8.5, base_ai_confidence + 2.0)
                        logger.info(f"Consensus signal ({consensus_count} strategies) - applying +2.0 bonus")
                    elif strategy_confidence >= 0.75:
                        # Single strategy with very high confidence - give bonus
                        ai_confidence = min(7.5, base_ai_confidence + 1.5)
                        logger.info(f"High confidence signal ({strategy_confidence:.2f}) - applying +1.5 bonus")
                    else:
                        # Still reliable but lower - smaller bonus
                        ai_confidence = min(7.0, base_ai_confidence + 1.0)
                else:
                    # Not highly reliable - keep conservative (small penalty for AI unavailability)
                    ai_confidence = max(1.0, base_ai_confidence - 0.5)
                
                # CRITICAL: If market is closed, apply SMALL penalty but don't kill signal
                if not market_open:
                    # Reduce confidence by 10% (0.9x) instead of capping at 5.0
                    original_confidence = ai_confidence
                    ai_confidence = ai_confidence * 0.9
                    logger.info(f"Market closed for {symbol}: confidence {original_confidence:.1f} → {ai_confidence:.1f} (10% penalty)")
                    # Still allow signal if above threshold after penalty
                
                # Ensure we don't go below 1.0 or above 10.0
                ai_confidence = max(1.0, min(10.0, ai_confidence))
                
                # Determine if this meets threshold (only approve if market is open AND confidence >= threshold)
                approved = ai_confidence >= self.confidence_threshold and market_open
                
                logger.info(f"Fallback confidence: {ai_confidence:.1f}/10 (from strategy confidence: {strategy_confidence:.2f}, threshold: {self.confidence_threshold:.1f}, reliable: {is_highly_reliable}, consensus: {consensus_count}, market_open: {market_open})")
                
                reasoning = f"⚠️ AI unavailable/timeout - using intelligent fallback. Strategy confidence: {strategy_confidence:.2f} → AI confidence: {ai_confidence:.1f}/10."
                if not market_open:
                    reasoning += f" ⚠️ Market is CLOSED for {symbol} - trading not recommended during closed hours."
                elif is_highly_reliable:
                    reasoning += " ✅ Bonus applied for highly reliable signal."
                else:
                    reasoning += " ⚠️ No bonus - signal not highly reliable."
                
                return {
                    "approved": approved,
                    "ai_confidence": ai_confidence,
                    "ai_reasoning": reasoning,
                    "market_open": market_open,
                }
            else:
                # Strategy confidence is 0 or missing - reject
                logger.warning("Strategy confidence is 0 - rejecting signal")
                return {
                    "approved": False,
                    "ai_confidence": 0.0,
                    "ai_reasoning": "AI unavailable and strategy confidence is 0 - rejecting signal",
                }
        
        # Log actual AI response for debugging (ALWAYS log to see what AI returns)
        logger.info(f"AI Response received (first 500 chars): {response[:500]}")
        
        # Parse AI response to extract verdict and confidence score
        ai_verdict = self._extract_verdict(response)
        ai_confidence = self._extract_confidence(response)
        ai_reasoning = response.strip()
        
        # Log extracted values (ALWAYS log to diagnose)
        logger.info(f"Extracted verdict: {ai_verdict}, confidence: {ai_confidence}")
        
        # Additional check: If market is closed, force lower confidence
        if not market_open:
            if ai_confidence > 5.0:
                logger.warning(f"Market is closed for {symbol}, but AI gave confidence {ai_confidence:.1f}. Reducing to 5.0.")
                ai_confidence = 5.0
                ai_reasoning += "\n⚠️ NOTE: Market is currently closed. Trading during closed hours is not recommended."
        
        # Determine approval: 
        # - If confidence >= threshold, approve (trust the confidence score even if verdict is REJECT)
        # - OR if verdict is APPROVE and confidence >= threshold
        # - Market must be open
        # FIX: Trust confidence score if it's above threshold, even if verdict says REJECT
        # This prevents AI from being overly conservative (confidence 6.0 but still REJECT)
        if ai_confidence >= self.confidence_threshold:
            # Confidence is above threshold - approve regardless of verdict
            # The confidence score is the primary filter, verdict is secondary
            approved = market_open
            if ai_verdict == "REJECT" and ai_confidence >= self.confidence_threshold:
                logger.info(f"AI gave REJECT verdict but confidence {ai_confidence:.1f} >= threshold {self.confidence_threshold:.1f} - approving based on confidence score")
        else:
            # Confidence below threshold - require APPROVE verdict
            approved = (ai_verdict == "APPROVE" and ai_confidence >= self.confidence_threshold and market_open)
        
        if not market_open:
            logger.info(f"Market is closed for {symbol} - signal will be rejected regardless of AI confidence")
        
        return {
            "approved": approved,
            "verdict": ai_verdict,
            "ai_confidence": ai_confidence,
            "ai_reasoning": ai_reasoning,
            "analysis": ai_reasoning,  # Alias for compatibility
            "market_open": market_open,
        }
    
    def _extract_verdict(self, response: str) -> str:
        """
        Extract verdict (APPROVE or REJECT) from AI response.
        Looks for patterns like "VERDICT: APPROVE" or "VERDICT: REJECT".
        """
        import re
        response_upper = response.upper()
        
        # Look for VERDICT: APPROVE or VERDICT: REJECT
        verdict_match = re.search(r'VERDICT:\s*(APPROVE|REJECT)', response_upper)
        if verdict_match:
            return verdict_match.group(1)
        
        # Fallback: Look for APPROVE or REJECT in response
        if 'APPROVE' in response_upper and 'REJECT' not in response_upper:
            return "APPROVE"
        elif 'REJECT' in response_upper:
            return "REJECT"
        
        # Default to REJECT if unclear
        return "REJECT"
    
    def _extract_confidence(self, response: str) -> float:
        """
        Extract confidence score (1-10) from AI response.
        Looks for patterns like "CONFIDENCE: 7" or "7/10" or "7.5".
        """
        # Try to find explicit confidence number - improved patterns
        patterns = [
            r"CONFIDENCE:\s*(\d+(?:\.\d+)?)",  # "CONFIDENCE: 7" or "CONFIDENCE: 7.5"
            r"confidence:\s*(\d+(?:\.\d+)?)",  # lowercase
            r"Confidence:\s*(\d+(?:\.\d+)?)",  # title case
            r"(\d+(?:\.\d+)?)/10",  # "7/10" or "7.5/10"
            r"rate[ds]?\s*(\d+(?:\.\d+)?)",  # "rated 7" or "rate 7.5"
            r"(\d+(?:\.\d+)?)\s*out\s*of\s*10",  # "7 out of 10"
            r"score[ds]?\s*(?:of\s*)?(\d+(?:\.\d+)?)",  # "score 7" or "score of 7.5"
            r"(\d+(?:\.\d+)?)\s*\/\s*10",  # "7 / 10" with spaces
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                try:
                    score = float(match.group(1))
                    # Clamp to 1-10 range
                    score = max(1.0, min(10.0, score))
                    logger.debug(f"Extracted confidence {score:.1f} using pattern: {pattern}")
                    return score
                except ValueError:
                    continue
        
        # If no explicit score found, try to infer from text
        # BUT: Be more conservative - only use strong indicators, not generic words
        response_lower = response.lower()
        
        # Check for explicit low confidence indicators FIRST (more specific)
        if any(phrase in response_lower for phrase in ["low confidence", "not recommended", "risky trade", "uncertain setup", "caution advised"]):
            logger.debug("Inferred low confidence (3.0) from negative phrases")
            return 3.0
        
        # Check for explicit high confidence indicators (more specific phrases)
        if any(phrase in response_lower for phrase in ["excellent setup", "strong signal", "very high confidence", "highly recommend", "strongly recommend"]):
            logger.debug("Inferred high confidence (8.0) from positive phrases")
            return 8.0
        
        # Medium confidence indicators (more specific)
        if any(phrase in response_lower for phrase in ["moderate confidence", "decent setup", "reasonable opportunity"]):
            logger.debug("Inferred medium confidence (6.0) from neutral phrases")
            return 6.0
        
        # Default to medium-low if can't determine - DON'T default to 8.0!
        logger.warning(f"Could not extract confidence score from AI response, defaulting to 5.0. Response preview: {response[:300]}")
        logger.warning(f"Full response length: {len(response)} chars. Please check if AI is following the format: 'CONFIDENCE: [1-10]'")
        return 5.0

