"""
Telegram Notification Service
Sends trading signal notifications via Telegram bot.
"""

import httpx
from typing import Dict, Any, Optional
from datetime import datetime
import sys
from pathlib import Path
import html

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.logger import logger


class TelegramNotifier:
    """
    Telegram bot notifier for sending signal notifications.
    """
    
    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize Telegram notifier.
        
        Args:
            bot_token: Telegram bot token from BotFather
            chat_id: Your Telegram chat ID (get from @userinfobot)
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        
        if not bot_token or not chat_id:
            logger.warning("Telegram bot token or chat ID not provided - notifications will be disabled")
    
    async def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """
        Send a plain text message to Telegram.
        
        Args:
            text: Message text
            parse_mode: "HTML" or "Markdown"
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram not configured: bot_token or chat_id missing")
            return False
        
        # Telegram has a 4096 character limit per message
        if len(text) > 4096:
            logger.warning(f"Message too long ({len(text)} chars), truncating to 4096...")
            text = text[:4090] + "\n..."
        
        try:
            logger.debug(f"Sending Telegram message to chat_id: {self.chat_id[:5]}...")
            response = httpx.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                },
                timeout=10,
            )
            response.raise_for_status()
            logger.debug(f"Telegram API response: {response.status_code}")
            return True
        except httpx.HTTPStatusError as e:
            # Provide more helpful error messages
            error_text = e.response.text if hasattr(e.response, 'text') else str(e.response)
            if e.response.status_code == 401:
                logger.error(f"❌ Telegram authentication failed (401). Check your TELEGRAM_BOT_TOKEN in .env file.")
                logger.error(f"Token format should be: '123456789:ABCdefGHIjklMNOpqrsTUVwxyz'")
                logger.error(f"Get your token from @BotFather on Telegram")
                logger.error(f"Response: {error_text}")
            elif e.response.status_code == 400:
                logger.error(f"❌ Telegram bad request (400). Check your TELEGRAM_CHAT_ID in .env file.")
                logger.error(f"Get your chat ID from @userinfobot on Telegram")
                logger.error(f"Response: {error_text}")
            elif e.response.status_code == 413:
                logger.error(f"❌ Telegram message too long (413). Message length: {len(text)} chars")
            else:
                logger.error(f"❌ Failed to send Telegram message: HTTP {e.response.status_code}")
                logger.error(f"Response: {error_text}")
            return False
        except httpx.TimeoutException:
            logger.error(f"❌ Telegram request timed out after 10 seconds")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to send Telegram message: {e}", exc_info=True)
            return False
    
    async def send_signal_notification(
        self,
        signal: Dict[str, Any],
        ai_result: Dict[str, Any]
    ) -> bool:
        """
        Send a formatted trading signal notification to Telegram.
        
        Args:
            signal: Signal dict with strategy, symbol, action, entry, sl, tp, confidence, timestamp
            ai_result: AI filter result with approved, ai_confidence, ai_reasoning
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.bot_token or not self.chat_id:
            return False
        
        # Format signal message
        action_emoji = "🟢" if signal.get("action") == "buy" else "🔴"
        strategy = signal.get("strategy", "unknown").replace("_", " ").title()
        
        # Extract live price data if available
        live_price_data = signal.get('_live_price_data')
        price_warning = signal.get('_price_warning')
        
        # Add live price status to message
        live_price_status = ""
        if live_price_data:
            price_age = live_price_data.get('age_seconds', 0.0)
            source = live_price_data.get('source', 'unknown')
            
            if source == "binance_live":
                live_price_status = f"\n✅ <b>Live Price:</b> Real-time from Binance (&lt;1s old)"
            elif price_age < 60:
                live_price_status = f"\n✅ <b>Live Price:</b> Fresh data ({price_age:.0f}s old)"
            elif price_age < 300:
                live_price_status = f"\n⚠️ <b>Price Age:</b> {price_age/60:.1f} minutes old"
            else:
                live_price_status = f"\n⚠️ <b>WARNING:</b> Price data is {price_age/60:.1f} minutes old - may be stale!"
        else:
            live_price_status = "\n⚠️ <b>WARNING:</b> Could not fetch live price - using cached data"
        
        # Add price movement warning if significant
        price_warning_text = ""
        if price_warning:
            movement = price_warning.get('movement_pct', 0.0)
            old_price = price_warning.get('old_price', 0.0)
            live_price = price_warning.get('live_price', 0.0)
            
            if abs(movement) > 2.0:
                price_warning_text = f"""

<b>⚠️ PRICE MOVEMENT ALERT:</b>
Signal generated at: ${old_price:.5f}
Current live price: ${live_price:.5f}
Movement: {movement:+.2f}%

<b>⚠️ EXECUTE WITH CAUTION - Price moved significantly!</b>
Consider waiting for pullback or skipping this signal.

"""
        
        # Calculate signal age (time from generation to notification)
        signal_generated_at = signal.get('signal_generated_at')
        signal_age_text = ""
        if signal_generated_at:
            try:
                from datetime import datetime
                if isinstance(signal_generated_at, str):
                    signal_generated_at = datetime.fromisoformat(signal_generated_at.replace('Z', '+00:00').split('+')[0])
                signal_age_seconds = (datetime.utcnow() - signal_generated_at).total_seconds()
                
                if signal_age_seconds < 60:
                    signal_age_text = f"{signal_age_seconds:.0f} seconds ago"
                else:
                    signal_age_text = f"{signal_age_seconds/60:.1f} minutes ago"
            except:
                pass
        
        # Add time-based information (signal age and estimated time to TP)
        price_trends = signal.get('price_trends', {})
        time_info = ""
        if price_trends:
            signal_age_minutes = price_trends.get('signal_age_minutes', 0.0)
            estimated_tp_minutes = price_trends.get('estimated_tp_time_minutes')
            change_1h = price_trends.get('change_1h_pct', 0.0)
            change_24h = price_trends.get('change_24h_pct', 0.0)
            
            # Format signal age (use signal_generated_at if available, otherwise use price_trends)
            if signal_age_text:
                age_text = signal_age_text
            elif signal_age_minutes < 1:
                age_text = "just now"
            elif signal_age_minutes < 60:
                age_text = f"{int(signal_age_minutes)} minute{'s' if int(signal_age_minutes) != 1 else ''} ago"
            else:
                hours = int(signal_age_minutes / 60)
                minutes = int(signal_age_minutes % 60)
                age_text = f"{hours}h {minutes}m ago"
            
            # Format estimated time to TP
            tp_time_text = ""
            if estimated_tp_minutes:
                if estimated_tp_minutes < 60:
                    tp_time_text = f"~{int(estimated_tp_minutes)} minute{'s' if int(estimated_tp_minutes) != 1 else ''}"
                else:
                    hours = int(estimated_tp_minutes / 60)
                    minutes = int(estimated_tp_minutes % 60)
                    tp_time_text = f"~{hours}h {minutes}m"
            
            time_info = f"""
<b>⏰ Time Info:</b>
  Signal generated: {age_text}
"""
            if tp_time_text:
                time_info += f"  Estimated to TP: {tp_time_text}\n"
            
            # Show price movement context (1h and 24h)
            trend_1h = price_trends.get('trend_1h', 'stable')
            trend_24h = price_trends.get('trend_24h', 'stable')
            trend_1h_emoji = "📈" if trend_1h == "rising" else ("📉" if trend_1h == "falling" else "➡️")
            trend_24h_emoji = "📈" if trend_24h == "rising" else ("📉" if trend_24h == "falling" else "➡️")
            
            time_info += f"""
<b>📊 Price Context:</b>
  1h: {trend_1h_emoji} {trend_1h.capitalize()} ({'+' if change_1h >= 0 else ''}{change_1h:.2f}%)
  24h: {trend_24h_emoji} {trend_24h.capitalize()} ({'+' if change_24h >= 0 else ''}{change_24h:.2f}%)
"""
        
        # Professional signal notification format
        emoji = "🚀" if signal.get("action") == "buy" else "📉"
        action_upper = signal.get("action", "unknown").upper()
        
        # Calculate risk/reward ratio
        entry = signal.get('entry', 0.0)
        stop_loss = signal.get('stop_loss', signal.get('sl', 0.0))
        take_profit = signal.get('take_profit', signal.get('tp', 0.0))
        
        if action_upper == "BUY":
            risk = entry - stop_loss
            reward = take_profit - entry
        else:
            risk = stop_loss - entry
            reward = entry - take_profit
        
        rr_ratio = reward / risk if risk > 0 else 0.0
        
        # Calculate percentages
        sl_pct = ((stop_loss - entry) / entry * 100) if entry > 0 else 0.0
        tp_pct = ((take_profit - entry) / entry * 100) if entry > 0 else 0.0
        
        # Get confirmations
        confirmations = signal.get('confirmations', [])
        confirmations_text = ', '.join(confirmations) if confirmations else 'None'
        
        # Get reasoning
        reasoning = signal.get('reasoning', 'No reasoning provided')
        
        # Get AI verdict
        ai_verdict = ai_result.get('verdict', 'APPROVE' if ai_result.get('approved', False) else 'REJECT')
        ai_confidence = ai_result.get('ai_confidence', 0.0)
        ai_analysis = ai_result.get('ai_reasoning', ai_result.get('analysis', 'No analysis provided'))
        
        # CRITICAL: Get expiration/duration information from signal
        duration_minutes = signal.get('duration_minutes')
        duration_hours = signal.get('duration_hours')
        expires_at_str = signal.get('expires_at')
        time_limit_message = signal.get('time_limit_message', '')
        
        # Format expiration information prominently
        expiration_info = ""
        if duration_minutes or expires_at_str:
            if expires_at_str:
                try:
                    # Handle ISO format with or without timezone
                    expires_at_str_clean = expires_at_str.replace('Z', '+00:00')
                    expires_at = datetime.fromisoformat(expires_at_str_clean)
                    expires_formatted = expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')
                except Exception as e:
                    # If parsing fails, use the string as-is
                    logger.debug(f"Could not parse expiration time '{expires_at_str}': {e}")
                    expires_formatted = expires_at_str
            else:
                expires_formatted = "Not specified"
            
            duration_text = ""
            if duration_minutes:
                if duration_minutes < 60:
                    duration_text = f"{int(duration_minutes)} minute{'s' if int(duration_minutes) != 1 else ''}"
                else:
                    hours = int(duration_minutes // 60)
                    mins = int(duration_minutes % 60)
                    if mins > 0:
                        duration_text = f"{hours}h {mins}m"
                    else:
                        duration_text = f"{hours} hour{'s' if hours != 1 else ''}"
            
            expiration_info = f"""
<b>⏰ TRADE DURATION & EXPIRATION:</b>
Duration: {duration_text if duration_text else 'Not specified'}
Expires At: {expires_formatted}
{time_limit_message if time_limit_message else '⚠️ Close trade at expiration time regardless of profit/loss'}
"""
        
        try:
            # CRITICAL: Escape all user-generated content to prevent HTML parsing errors
            # Only escape text content, NOT HTML tags (b, i, etc.)
            def escape_text(text: str) -> str:
                """Escape text but preserve HTML tags"""
                if not text:
                    return ""
                # Escape HTML entities but keep valid HTML tags
                # Telegram supports: <b>, <i>, <u>, <s>, <a>, <code>, <pre>
                # We need to escape < and > that are NOT part of valid tags
                # Simple approach: escape everything, then restore valid tags
                escaped = html.escape(str(text))
                # Restore valid HTML tags we want to keep
                valid_tags = ['<b>', '</b>', '<i>', '</i>', '<u>', '</u>', '<s>', '</s>', 
                             '<a href=', '</a>', '<code>', '</code>', '<pre>', '</pre>']
                for tag in valid_tags:
                    # Restore tag from escaped version
                    tag_escaped = html.escape(tag)
                    escaped = escaped.replace(tag_escaped, tag)
                return escaped
            
            # Escape all dynamic content
            safe_strategy = escape_text(strategy)
            safe_symbol = escape_text(signal.get('symbol', 'unknown'))
            safe_reasoning = escape_text(reasoning)
            safe_confirmations = escape_text(confirmations_text)
            safe_ai_verdict = escape_text(ai_verdict)
            safe_ai_analysis = escape_text(ai_analysis)
            safe_timestamp = escape_text(signal.get('timestamp', 'unknown'))
            
            message = f"""{emoji} <b>PROFESSIONAL SIGNAL ALERT</b>

<b>Strategy:</b> {safe_strategy}
<b>Asset:</b> {safe_symbol}
<b>Action:</b> {action_upper}
<b>Entry:</b> ${entry:,.4f}{live_price_status}

{price_warning_text}
<b>Risk Management:</b>
Stop Loss: ${stop_loss:,.4f} ({sl_pct:+.2f}%)
Take Profit: ${take_profit:,.4f} ({tp_pct:+.2f}%)
Risk/Reward: {rr_ratio:.2f}:1
{expiration_info}
<b>Technical Analysis:</b>
{safe_reasoning}

<b>Confirmations:</b> {safe_confirmations}

<b>AI Verdict:</b> {safe_ai_verdict} ({ai_confidence:.1f}/10)
{safe_ai_analysis}

<b>Timestamp:</b> {safe_timestamp}

⚠️ This is not financial advice. Trade at your own risk."""
            
            logger.info(f"Attempting to send Telegram message (length: {len(message)} chars)")
            result = await self.send_message(message.strip())
            
            if result:
                logger.info(f"✅ Telegram message sent successfully")
            else:
                logger.error(f"❌ Telegram send_message returned False")
            
            return result
        except Exception as e:
            logger.error(f"❌ Exception formatting/sending Telegram message: {e}", exc_info=True)
            return False
    
    async def send_daily_summary(self, summary: Dict[str, Any]) -> bool:
        """
        Send a daily summary of signal activity.
        
        Args:
            summary: Dict with total_signals, ai_filtered, telegram_sent, by_strategy
        
        Returns:
            True if sent successfully, False otherwise
        """
        message = f"""
📊 <b>Daily Signal Summary</b>

<b>Total Signals:</b> {summary.get('total_signals', 0)}
<b>AI Filtered:</b> {summary.get('ai_filtered', 0)}
<b>Notifications Sent:</b> {summary.get('telegram_sent', 0)}

<b>By Strategy:</b>
"""
        
        by_strategy = summary.get('by_strategy', {})
        for strategy, count in sorted(by_strategy.items(), key=lambda x: x[1], reverse=True):
            message += f"  • {strategy.replace('_', ' ').title()}: {count}\n"
        
        return await self.send_message(message.strip())

