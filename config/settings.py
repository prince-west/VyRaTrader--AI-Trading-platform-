"""
Configuration settings for the Signal Generator.
Loads from .env file and config.json.
"""

import os
import json
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class SignalGeneratorConfig:
    """
    Configuration for the signal generator.
    Loads from environment variables (.env) and config.json.
    Uses direct os.getenv() to avoid pydantic validation errors with extra fields.
    """
    
    def __init__(self):
        # Telegram Configuration
        self.TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
        
        # AI Configuration
        self.AI_PROVIDER: str = os.getenv("AI_PROVIDER", "ollama")  # ollama, groq, huggingface
        self.AI_MODEL: str = os.getenv("AI_MODEL", "llama3.1")  # llama3.1 for ollama, llama-3.1-8b-8192 for groq
        self.AI_CONFIDENCE_THRESHOLD: float = float(os.getenv("AI_CONFIDENCE_THRESHOLD", "7.0"))
        
        # Fallback AI Provider API Keys
        self.GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY", None)
        self.HUGGINGFACE_API_KEY: Optional[str] = os.getenv("HUGGINGFACE_API_KEY", None)
        
        # Market Data Configuration (from config.json or defaults)
        self.ASSETS: List[str] = []
        self.CRYPTO_SYMBOLS: List[str] = []
        self.COINGECKO_IDS: List[str] = []
        self.FOREX_PAIRS: List[str] = []
        
        # Polling Configuration
        self.POLLING_INTERVAL: int = int(os.getenv("POLLING_INTERVAL", "60"))  # seconds
        
        # Strategy Sensitivity (from config.json)
        self.STRATEGY_SETTINGS: dict = {}
        
        # Load config.json
        self._load_config_json()
    
    def _load_config_json(self) -> None:
        """Load additional configuration from config.json."""
        config_file = Path("config.json")
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                
                # Load assets to monitor
                if "assets" in config_data:
                    self.ASSETS = config_data["assets"]
                    # Extract crypto symbols from assets (everything that's not forex)
                    self.CRYPTO_SYMBOLS = [
                        asset for asset in self.ASSETS 
                        if not any(asset.startswith(prefix) for prefix in ["EUR", "USD", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD"]) or "USDT" in asset
                    ]
                    # Extract forex pairs from assets (if not explicitly set)
                    if "forex_pairs" not in config_data:
                        self.FOREX_PAIRS = [
                            asset for asset in self.ASSETS 
                            if any(asset.startswith(prefix) for prefix in ["EUR", "USD", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD"]) and "USDT" not in asset
                        ]
                
                # Load coingecko IDs (for crypto assets)
                if "coingecko_ids" in config_data:
                    self.COINGECKO_IDS = config_data["coingecko_ids"]
                
                # Load forex pairs (for forex assets)
                if "forex_pairs" in config_data:
                    self.FOREX_PAIRS = config_data["forex_pairs"]
                
                # Load strategy sensitivity settings
                if "strategy_sensitivity" in config_data:
                    self.STRATEGY_SETTINGS = config_data["strategy_sensitivity"]
                
                # Override polling interval if specified
                if "polling_interval" in config_data:
                    self.POLLING_INTERVAL = config_data["polling_interval"]
                
                # Override AI confidence threshold if specified
                if "ai_confidence_threshold" in config_data:
                    self.AI_CONFIDENCE_THRESHOLD = config_data["ai_confidence_threshold"]
                
            except Exception as e:
                print(f"Warning: Error loading config.json: {e}")
                print("Using default configuration")
        
        # Set defaults if not configured
        if not self.ASSETS:
            self.ASSETS = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
            self.CRYPTO_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
            self.COINGECKO_IDS = ["bitcoin", "ethereum", "binancecoin"]
            self.FOREX_PAIRS = []  # No forex by default, but can be added


# Global config instance
config = SignalGeneratorConfig()

