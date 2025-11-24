@echo off
echo Starting VyRaTrader Signal Generator...
echo.

REM Check if Ollama is running
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% neq 0 (
    echo Warning: Cannot connect to Ollama at http://localhost:11434
    echo Make sure Ollama is running!
    echo.
    echo To start Ollama:
    echo 1. Open Ollama from Start Menu
    echo 2. Or run: ollama serve
    echo.
    pause
)

echo ✅ All checks passed
echo Starting signal generator...
echo.

python signal_generator.py

pause

