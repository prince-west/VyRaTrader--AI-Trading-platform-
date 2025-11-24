# backend/app/seed.py
"""
Seed script: create test user test@vyra.local with password Password123! and an account with GHS 10000
Run: python -m backend.app.seed
"""
import asyncio
from backend.app.db.session import init_db, async_session
from backend.app.db.models import User, Account
from passlib.context import CryptContext

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def seed():
    await init_db()
    async with async_session() as session:
        # Check if user exists
        from sqlalchemy import select
        q = await session.exec(select(User).where(User.email == "test@vyra.local"))
        user = q.first()
        if user:
            print("Seed: test user exists")
            return
        user = User(email="test@vyra.local", password_hash=pwd.hash("Password123!"), full_name="Test User")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        acct = Account(user_id=user.id, currency="GHS", available_balance=10000.0, ledger_balance=10000.0)
        session.add(acct)
        await session.commit()
        print("Seed: created test user and account")


if __name__ == "__main__":
    asyncio.run(seed())
