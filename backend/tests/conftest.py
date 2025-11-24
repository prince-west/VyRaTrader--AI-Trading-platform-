# backend/tests/conftest.py
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.app.main import app
from backend.app.db.session import engine, get_session


# ✅ Ensure module-scoped event loop so prepare_database works without ScopeMismatch
@pytest.fixture(scope="module")
def event_loop():
    """Create a single event loop for the whole test module."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module", autouse=True)
async def prepare_database():
    """Create a fresh test DB schema for the whole test module."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def session():
    async with AsyncSession(engine) as s:
        yield s


@pytest_asyncio.fixture
async def client(session):
    """HTTPX AsyncClient with DB session override for the app."""
    async def _get_test_session():
        yield session

    app.dependency_overrides[get_session] = _get_test_session
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
