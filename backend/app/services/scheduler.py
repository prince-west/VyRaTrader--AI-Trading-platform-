"""
Background scheduler for periodic data collection and premium expiration.
- start_background_tasks(app, interval_seconds): creates an asyncio Task running data collection.
- stop_background_tasks(): cancels the task and awaits cleanup.
"""

from __future__ import annotations

import asyncio
from typing import Optional
from datetime import datetime, timezone

from fastapi import FastAPI

from backend.app.core.logger import logger
from backend.app.services import data_collector
from backend.app.db.session import get_session
from backend.app.db.models import User
from sqlmodel import select, update


_TASK_ATTR = "vyra_bg_task"
_PREMIUM_EXPIRY_TASK_ATTR = "vyra_premium_expiry_task"


def _get_task(app: FastAPI) -> Optional[asyncio.Task]:
    return getattr(app.state, _TASK_ATTR, None)


async def _expire_premium_users() -> None:
    """
    Daily task to expire premium users whose subscription has ended.
    Runs at midnight UTC and checks all users with expired premium.
    """
    try:
        async for session in get_session():
            now = datetime.now(timezone.utc)
            
            # Find users with expired premium
            stmt = (
                select(User)
                .where(User.is_premium == True)
                .where(User.premium_expires_at <= now)
            )
            result = await session.exec(stmt)
            expired_users = result.all()
            
            if expired_users:
                # Update expired users
                update_stmt = (
                    update(User)
                    .where(User.id.in_([u.id for u in expired_users]))
                    .values(is_premium=False, premium_expires_at=None)
                )
                await session.exec(update_stmt)
                await session.commit()
                
                logger.info(f"Expired premium for {len(expired_users)} users")
            else:
                logger.debug("No expired premium users found")
            
            break  # Only process one session
    except Exception as e:
        logger.exception(f"Error expiring premium users: {e}")


async def _run_daily_tasks() -> None:
    """
    Daily task runner - expires premium users at midnight UTC.
    Checks every hour if it's midnight, then runs expiration.
    """
    while True:
        try:
            now = datetime.now(timezone.utc)
            # Run at midnight UTC (00:00)
            if now.hour == 0 and now.minute < 5:  # Give 5 minute window
                logger.info("Running daily premium expiration task")
                await _expire_premium_users()
                # Wait until next hour to avoid multiple runs
                await asyncio.sleep(3600)
            else:
                # Check every hour
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.exception(f"Error in daily premium expiry task: {e}")
            await asyncio.sleep(3600)  # Wait before retry


def start_background_tasks(app: FastAPI, interval_seconds: int = 60) -> None:
    if _get_task(app) is not None:
        logger.info("Background task already running; skipping start.")
        return
    async def runner() -> None:
        await data_collector.run_periodic(interval_seconds=interval_seconds)

    task = asyncio.create_task(runner(), name="vyra_data_collector")
    setattr(app.state, _TASK_ATTR, task)
    logger.info("Background data collector task started (interval=%ss).", interval_seconds)
    
    # Start premium expiration task
    premium_task = asyncio.create_task(_run_daily_tasks(), name="vyra_premium_expiry")
    setattr(app.state, _PREMIUM_EXPIRY_TASK_ATTR, premium_task)
    logger.info("Premium expiration task started (daily at midnight UTC).")


async def stop_background_tasks(app: Optional[FastAPI] = None) -> None:
    task: Optional[asyncio.Task] = None
    if app is not None:
        task = _get_task(app)
    if task is None:
        logger.info("No background task to stop.")
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.info("Background task cancelled.")
    finally:
        if app is not None:
            setattr(app.state, _TASK_ATTR, None)
        logger.info("Background tasks stopped.")


