#!/usr/bin/env python3
"""
Quick test script to verify Telegram bot token and chat ID
"""
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("TELEGRAM_BOT_TOKEN", "")
chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

print("Testing Telegram configuration...")
print()

if not token:
    print("[ERROR] TELEGRAM_BOT_TOKEN not set in .env file")
    exit(1)

if not chat_id:
    print("[ERROR] TELEGRAM_CHAT_ID not set in .env file")
    exit(1)

print(f"Token length: {len(token)}")
print(f"Token format: {'OK' if ':' in token else 'INVALID'} (should contain ':')")
print(f"Chat ID: {chat_id}")
print()

# Test 1: Verify bot token
print("Test 1: Verifying bot token...")
try:
    response = httpx.get(
        f"https://api.telegram.org/bot{token}/getMe",
        timeout=5
    )
    if response.status_code == 200:
        data = response.json()
        if data.get("ok"):
            bot_info = data.get("result", {})
            print(f"[OK] Bot token is valid!")
            print(f"   Bot name: {bot_info.get('first_name', 'Unknown')}")
            print(f"   Bot username: @{bot_info.get('username', 'Unknown')}")
        else:
            print(f"[ERROR] Bot token verification failed: {data}")
    else:
        print(f"[ERROR] Bot token is invalid (status {response.status_code})")
        print(f"   Response: {response.text}")
        print()
        print("How to fix:")
        print("1. Open Telegram and search for @BotFather")
        print("2. Send /mybots and select your bot")
        print("3. Click 'API Token' and copy the token")
        print("4. Update TELEGRAM_BOT_TOKEN in .env file")
        exit(1)
except Exception as e:
    print(f"❌ Error testing bot token: {e}")
    exit(1)

print()

# Test 2: Send test message
print("Test 2: Sending test message...")
try:
    response = httpx.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": "✅ Telegram bot is working! Your signal generator can now send notifications.",
            "parse_mode": "HTML",
        },
        timeout=10,
    )
    if response.status_code == 200:
        data = response.json()
        if data.get("ok"):
            print("[OK] Test message sent successfully!")
            print(f"   Check your Telegram - you should see a test message")
        else:
            print(f"[ERROR] Failed to send message: {data}")
    else:
        print(f"[ERROR] Failed to send message (status {response.status_code})")
        if response.status_code == 400:
            print(f"   Response: {response.text}")
            print()
            print("How to fix:")
            print("1. Open Telegram and search for @userinfobot")
            print("2. Send /start to get your chat ID")
            print("3. Update TELEGRAM_CHAT_ID in .env file")
        elif response.status_code == 401:
            print(f"   Response: {response.text}")
            print()
            print("How to fix:")
            print("1. Open Telegram and search for @BotFather")
            print("2. Send /mybots and select your bot")
            print("3. Click 'API Token' and copy the token")
            print("4. Update TELEGRAM_BOT_TOKEN in .env file")
        exit(1)
except Exception as e:
    print(f"❌ Error sending test message: {e}")
    exit(1)

print()
print("[OK] All tests passed! Telegram is configured correctly.")

