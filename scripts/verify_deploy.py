#!/usr/bin/env python3
import os
import sys
import logging
from datetime import datetime, timedelta
from typing import List, Dict

import requests
import sqlalchemy as sa
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Config
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///vyra.db")
API_BASE = os.getenv("API_BASE", "http://localhost:8000")
REQUIRED_TABLES = ["strategies", "trades", "users", "price_ticks"]
API_TIMEOUT = 10  # seconds

def check_database() -> bool:
    """Verify database connection and required tables exist."""
    try:
        engine = create_engine(DATABASE_URL)
        inspector = sa.inspect(engine)
        existing_tables = inspector.get_table_names()
        
        missing = [t for t in REQUIRED_TABLES if t not in existing_tables]
        if missing:
            logger.error("Missing tables: %s", missing)
            return False
            
        # Check price_ticks data
        with engine.connect() as conn:
            # Get counts per source for last 5 days
            query = text("""
                SELECT source, COUNT(*) as count 
                FROM price_ticks 
                WHERE timestamp > :since
                GROUP BY source
                ORDER BY count DESC
            """)
            since = datetime.utcnow() - timedelta(days=5)
            results = conn.execute(query, {"since": since}).fetchall()
            
            if not results:
                logger.error("No recent price ticks found")
                return False
                
            logger.info("Price ticks last 5 days:")
            for source, count in results:
                logger.info("  %s: %d", source, count)
                
        return True
        
    except SQLAlchemyError as e:
        logger.error("Database check failed: %s", e)
        return False

def check_api() -> bool:
    """Verify critical API endpoints are responding."""
    endpoints = {
        "/health": 200,
        "/api/v1/signals/latest": 200
    }
    
    try:
        for path, expected_status in endpoints.items():
            url = f"{API_BASE}{path}"
            r = requests.get(url, timeout=API_TIMEOUT)
            
            if r.status_code != expected_status:
                logger.error(
                    "Endpoint %s returned %d (expected %d)",
                    path, r.status_code, expected_status
                )
                return False
                
            logger.info("Endpoint %s OK (%dms)", path, r.elapsed.microseconds/1000)
            
        return True
        
    except requests.RequestException as e:
        logger.error("API check failed: %s", e)
        return False

def main():
    logger.info("Starting deployment verification")
    
    db_ok = check_database()
    logger.info("Database check: %s", "PASS" if db_ok else "FAIL")
    
    api_ok = check_api()
    logger.info("API check: %s", "PASS" if api_ok else "FAIL")
    
    if not (db_ok and api_ok):
        logger.error("Verification failed")
        sys.exit(1)
        
    logger.info("All checks passed")
    sys.exit(0)

if __name__ == "__main__":
    main()
