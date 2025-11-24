#!/usr/bin/env python3
"""
Quick test script to verify setup
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

print("Testing setup...")
print()

# Test imports
try:
    from app.core.logger import logger
    print("[OK] Logger imported")
except Exception as e:
    print(f"[ERROR] Logger import failed: {e}")

try:
    from app.db.session import get_session
    print("[OK] Database session imported")
except Exception as e:
    print(f"[ERROR] Database session import failed: {e}")

try:
    import sys
    from pathlib import Path
    # Make sure we're importing from the right place
    if str(Path(__file__).parent) not in sys.path:
        sys.path.insert(0, str(Path(__file__).parent))
    from config.settings import SignalGeneratorConfig
    config = SignalGeneratorConfig()
    print("[OK] Signal Generator Config loaded")
    
    if config.TELEGRAM_BOT_TOKEN:
        print(f"   - Telegram Bot Token: {'*' * 20} (configured)")
    else:
        print("   - Telegram Bot Token: NOT SET")
    
    if config.TELEGRAM_CHAT_ID:
        print(f"   - Telegram Chat ID: {config.TELEGRAM_CHAT_ID}")
    else:
        print("   - Telegram Chat ID: NOT SET")
    
    print(f"   - AI Provider: {config.AI_PROVIDER}")
    print(f"   - AI Model: {config.AI_MODEL}")
    print(f"   - Assets: {len(config.ASSETS)} configured")
except Exception as e:
    print(f"[ERROR] Config load failed: {e}")
    import traceback
    traceback.print_exc()

# Test Ollama connection
try:
    import httpx
    response = httpx.get("http://localhost:11434/api/tags", timeout=5)
    if response.status_code == 200:
        print("✅ Ollama is running and accessible")
        data = response.json()
        models = [m.get("name", "") for m in data.get("models", [])]
        if "llama3.1" in str(models):
            print("   - llama3.1 model found")
        else:
            print("   - llama3.1 model not found (run: ollama pull llama3.1)")
    else:
        print(f"⚠️  Ollama responded with status {response.status_code}")
except httpx.ConnectError:
    print("❌ Cannot connect to Ollama")
    print("   Make sure Ollama is running (check system tray or run: ollama serve)")
except Exception as e:
    print(f"⚠️  Ollama check failed: {e}")

# Test Telegram
try:
    import httpx
    from config.settings import SignalGeneratorConfig
    config = SignalGeneratorConfig()
    
    if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID:
        response = httpx.get(
            f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getMe",
            timeout=5
        )
        if response.status_code == 200:
            print("[OK] Telegram bot is configured correctly")
        else:
            print(f"[WARNING] Telegram bot check failed: {response.status_code}")
            print(f"   Response: {response.text}")
    else:
        print("[WARNING] Telegram not configured (missing token or chat ID)")
except Exception as e:
    print(f"[WARNING] Telegram check failed: {e}")

print()
print("Setup test complete!")
print()

