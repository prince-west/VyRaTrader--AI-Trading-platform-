# backend/app/core/logger.py
from loguru import logger
import os

LOG_DIR = os.path.join(os.getcwd(), "backend", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logger.add(
    os.path.join(LOG_DIR, "vyra_trader.log"),
    rotation="10 MB",
    retention="14 days",
    level="INFO",
    backtrace=True,
    diagnose=False,
)
