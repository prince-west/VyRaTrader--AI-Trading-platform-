"""
AI Setup and Diagnostic Script
Checks AI provider configuration and provides setup instructions.
"""

import sys
import httpx
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

def check_ollama():
    """Check if Ollama is installed and running."""
    print("=" * 60)
    print("Checking Ollama Setup...")
    print("=" * 60)
    
    # Check if Ollama service is running
    try:
        response = httpx.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print("[OK] Ollama is running!")
            print(f"   Found {len(models)} model(s):")
            for model in models:
                model_name = model.get("name", "unknown")
                size = model.get("size", 0) / (1024**3)  # Convert to GB
                print(f"   - {model_name} ({size:.2f} GB)")
            
            # Check if llama3.1 is available
            has_llama = any("llama3.1" in m.get("name", "").lower() for m in models)
            if has_llama:
                print("[OK] llama3.1 model is available!")
            else:
                print("[WARN] llama3.1 model not found. Run: ollama pull llama3.1")
            
            return True
        else:
            print(f"[ERROR] Ollama responded with status {response.status_code}")
            return False
    except httpx.ConnectError:
        print("[ERROR] Cannot connect to Ollama (not running)")
        print("\nSetup Instructions:")
        print("   1. Download Ollama from: https://ollama.ai/download")
        print("   2. Install Ollama")
        print("   3. Start Ollama service (should start automatically)")
        print("   4. Pull the model: ollama pull llama3.1")
        print("   5. Or use faster model: ollama pull llama3.1:8b")
        return False
    except Exception as e:
        print(f"[ERROR] Error checking Ollama: {e}")
        return False

def check_groq():
    """Check if Groq API key is configured."""
    print("\n" + "=" * 60)
    print("Checking Groq Setup...")
    print("=" * 60)
    
    # Check for API key in environment
    api_key = os.getenv("GROQ_API_KEY")
    if api_key:
        print("[OK] GROQ_API_KEY is set in environment")
        print(f"   Key: {api_key[:10]}...{api_key[-4:]}")
        
        # Test API connection
        try:
            response = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [{"role": "user", "content": "test"}],
                },
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )
            if response.status_code == 200:
                print("[OK] Groq API connection successful!")
                return True
            else:
                print(f"[WARN] Groq API returned status {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False
        except Exception as e:
            print(f"[ERROR] Groq API test failed: {e}")
            return False
    else:
        print("[WARN] GROQ_API_KEY not found in environment")
        print("\nSetup Instructions:")
        print("   1. Get free API key from: https://console.groq.com/")
        print("   2. Add to .env file: GROQ_API_KEY=your_key_here")
        print("   3. Set AI_PROVIDER=groq in .env")
        print("   4. Set AI_MODEL=llama-3.1-8b-8192 in .env")
        return False

def check_config():
    """Check current AI configuration."""
    print("\n" + "=" * 60)
    print("Checking AI Configuration...")
    print("=" * 60)
    
    # Check .env file
    env_file = Path(".env")
    if env_file.exists():
        print("[OK] .env file found")
        with open(env_file, "r") as f:
            content = f.read()
            if "AI_PROVIDER" in content:
                provider = [line for line in content.split("\n") if "AI_PROVIDER" in line and not line.strip().startswith("#")]
                if provider:
                    print(f"   {provider[0].strip()}")
            if "AI_MODEL" in content:
                model = [line for line in content.split("\n") if "AI_MODEL" in line and not line.strip().startswith("#")]
                if model:
                    print(f"   {model[0].strip()}")
            if "AI_CONFIDENCE_THRESHOLD" in content:
                threshold = [line for line in content.split("\n") if "AI_CONFIDENCE_THRESHOLD" in line and not line.strip().startswith("#")]
                if threshold:
                    print(f"   {threshold[0].strip()}")
    else:
        print("[WARN] .env file not found")
        print("   Create .env file with AI configuration")
    
    # Check config.json
    config_file = Path("config.json")
    if config_file.exists():
        import json
        with open(config_file, "r") as f:
            config = json.load(f)
            if "ai_confidence_threshold" in config:
                print(f"[OK] config.json: ai_confidence_threshold = {config['ai_confidence_threshold']}")

def provide_recommendations(ollama_ok, groq_ok):
    """Provide recommendations based on check results."""
    print("\n" + "=" * 60)
    print("Recommendations")
    print("=" * 60)
    
    if ollama_ok:
        print("[OK] Ollama is working - you can use it as your AI provider")
        print("   Current config: AI_PROVIDER=ollama, AI_MODEL=llama3.1")
        print("\nPerformance Tips:")
        print("   - If Ollama is slow, use smaller model: ollama pull llama3.1:8b")
        print("   - Or use quantized version: ollama pull llama3.1:8b-q4_0")
        print("   - Update .env: AI_MODEL=llama3.1:8b")
    elif groq_ok:
        print("[OK] Groq is working - recommended for faster responses")
        print("   Current config: AI_PROVIDER=groq")
        print("   Groq is much faster than local Ollama (GPU-accelerated)")
    else:
        print("[WARN] No AI provider is currently working")
        print("\nQuick Setup Options:")
        print("\nOption 1: Setup Ollama (Free, Local)")
        print("   1. Download: https://ollama.ai/download")
        print("   2. Install and start Ollama")
        print("   3. Run: ollama pull llama3.1:8b")
        print("   4. Add to .env: AI_PROVIDER=ollama, AI_MODEL=llama3.1:8b")
        print("\nOption 2: Setup Groq (Free, Fast, Cloud)")
        print("   1. Get API key: https://console.groq.com/")
        print("   2. Add to .env:")
        print("      AI_PROVIDER=groq")
        print("      AI_MODEL=llama-3.1-8b-8192")
        print("      GROQ_API_KEY=your_key_here")
        print("\nOption 3: Use Fallback Mode (No AI)")
        print("   - System will use intelligent fallback when AI is unavailable")
        print("   - Add to .env: AI_CONFIDENCE_THRESHOLD=0.0")
        print("   - Signals will be sent without AI filtering")

def main():
    """Run all checks and provide recommendations."""
    print("\n" + "=" * 60)
    print("AI Setup Diagnostic Tool")
    print("=" * 60)
    print()
    
    ollama_ok = check_ollama()
    groq_ok = check_groq()
    check_config()
    provide_recommendations(ollama_ok, groq_ok)
    
    print("\n" + "=" * 60)
    print("[OK] Diagnostic Complete")
    print("=" * 60)

if __name__ == "__main__":
    main()

