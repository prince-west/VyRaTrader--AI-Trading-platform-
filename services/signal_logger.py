"""
Signal Logger Service
Logs all signals (including filtered ones) to signals.json and generates daily summaries.
"""

import json
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List
from collections import defaultdict
import sys

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.logger import logger


class SignalLogger:
    """
    Logger for trading signals with JSON storage and daily summaries.
    """
    
    def __init__(self, log_file: str = "signals.json"):
        """
        Initialize signal logger.
        
        Args:
            log_file: Path to JSON file for storing signals
        """
        self.log_file = Path(log_file)
        self.signals_today: List[Dict[str, Any]] = []
        
        # Ensure log directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    async def log_signal(self, signal: Dict[str, Any]) -> None:
        """
        Log a signal to signals.json.
        
        Args:
            signal: Signal dict with all details
        """
        try:
            # Load existing signals
            existing_signals = []
            if self.log_file.exists():
                with open(self.log_file, 'r') as f:
                    try:
                        existing_signals = json.load(f)
                    except json.JSONDecodeError:
                        existing_signals = []
            
            # CRITICAL: Convert datetime objects to ISO strings for JSON serialization
            def convert_datetime(obj):
                """Recursively convert datetime objects to ISO strings."""
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {k: convert_datetime(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_datetime(item) for item in obj]
                return obj
            
            # Convert signal to JSON-serializable format
            signal_serializable = convert_datetime(signal)
            
            # Add new signal with timestamp
            signal_entry = {
                "logged_at": datetime.utcnow().isoformat(),
                "signal": signal_serializable,
            }
            
            existing_signals.append(signal_entry)
            
            # Keep only last 10,000 signals to prevent file from growing too large
            if len(existing_signals) > 10000:
                existing_signals = existing_signals[-10000:]
            
            # Write back
            with open(self.log_file, 'w') as f:
                json.dump(existing_signals, f, indent=2)
            
            # Track for daily summary (use original signal, not serialized)
            self.signals_today.append(signal)
            
        except Exception as e:
            logger.error(f"Error logging signal: {e}")
    
    def generate_daily_summary(self) -> Dict[str, Any]:
        """
        Generate a daily summary of signal activity.
        
        Returns:
            Dict with summary statistics
        """
        if not self.signals_today:
            return {
                "date": date.today().isoformat(),
                "total_signals": 0,
                "by_strategy": {},
            }
        
        # Count by strategy
        by_strategy = defaultdict(int)
        actions = defaultdict(int)
        
        for signal in self.signals_today:
            strategy = signal.get("strategy", "unknown")
            action = signal.get("action", "unknown")
            by_strategy[strategy] += 1
            actions[action] += 1
        
        summary = {
            "date": date.today().isoformat(),
            "total_signals": len(self.signals_today),
            "by_strategy": dict(by_strategy),
            "by_action": dict(actions),
        }
        
        # Write summary to file
        summary_file = Path("daily_summaries") / f"summary_{date.today().isoformat()}.json"
        summary_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
            
            logger.info(f"📊 Daily summary saved to {summary_file}")
        except Exception as e:
            logger.error(f"Error saving daily summary: {e}")
        
        return summary

